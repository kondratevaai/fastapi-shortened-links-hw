import secrets
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from domain.models import User, ShortenedLink
from schemas.schemas import (
    ShortenLinkRequest, 
    ShortenedLinkResponse, 
    LinkStatsResponse,
    UpdateLinkRequest
)
from auth.dependencies import get_current_user
from services.cache import cache


router = APIRouter(
    prefix="/links",
    tags=["Link management"]
)


def generate_short_code(length: int = 6) -> str:
    
    # generate random short code for url shortening:
    chars = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
    return "".join(secrets.choice(chars) for _ in range(length))


@router.post("/shorten", response_model=ShortenedLinkResponse)
async def shorten_link(
    request: ShortenLinkRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> ShortenedLink:
    """unit to create new shortened link or use custom alias if provided"""
    
    # check whether custom alias already exists:
    if request.custom_alias:
        result = await db.execute(
            select(ShortenedLink).where(
                ShortenedLink.custom_alias == request.custom_alias
            )
        )
        if result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="custom alias already exists"
            )
        short_code = request.custom_alias
    else:
        # generate unique short code:
        while True:
            short_code = generate_short_code()
            result = await db.execute(
                select(ShortenedLink).where(
                    ShortenedLink.short_code == short_code
                )
            )
            if not result.scalar_one_or_none():
                break

    # create new link record:
    new_link = ShortenedLink(
        short_code=short_code,
        original_url=request.original_url,
        custom_alias=request.custom_alias,
        user_id=current_user.id,
        expires_at=request.expires_at
    )

    db.add(new_link)
    await db.commit()
    await db.refresh(new_link)

    return new_link


@router.get("/{short_code}", response_model=ShortenedLinkResponse)
async def redirect_to_url(
    short_code: str,
    db: AsyncSession = Depends(get_db)
) -> ShortenedLink:
    """ redirect to original url and increment click count"""
    
    # check cache first for frequently accessed links:
    cached_link = await cache.get_link(short_code)
    if cached_link:
        # increment click count in cache and db:
        cache_clicks = await cache.increment_click_count(short_code)
        
        # update clicks in database asynchronously:
        result = await db.execute(
            select(ShortenedLink).where(
                ShortenedLink.short_code == short_code
            )
        )
        link = result.scalar_one_or_none()
        if link:
            link.click_count += 1
            link.last_accessed_at = datetime.utcnow()
            db.add(link)
            await db.commit()
        
        return ShortenedLink(**cached_link) if isinstance(cached_link, dict) else cached_link
    
    # find the shortened link in database:
    result = await db.execute(
        select(ShortenedLink).where(
            and_(
                ShortenedLink.short_code == short_code
            )
        )
    )
    link = result.scalar_one_or_none()

    if not link:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="shortened link not found"
        )

    # check if link has expired:
    if link.expires_at and link.expires_at < datetime.utcnow():
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail="link has expired"
        )

    # increment click count and update last accessed time:
    link.click_count += 1
    link.last_accessed_at = datetime.utcnow()

    db.add(link)
    await db.commit()
    await db.refresh(link)
    
    # increment click count in redis cache FIRST (for accurate click tracking):
    await cache.increment_click_count(short_code)
    
    # then cache this link for future requests:
    link_dict = {
        "id": link.id,
        "short_code": link.short_code,
        "original_url": link.original_url,
        "custom_alias": link.custom_alias,
        "user_id": link.user_id,
        "click_count": link.click_count,
        "created_at": link.created_at.isoformat() if link.created_at else None,
        "last_accessed_at": link.last_accessed_at.isoformat() if link.last_accessed_at else None,
        "expires_at": link.expires_at.isoformat() if link.expires_at else None,
    }
    await cache.set_link(short_code, link_dict)

    return link


@router.get("/{short_code}/stats", response_model=LinkStatsResponse)
async def get_link_stats(
    short_code: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> dict:
    """ Get statistics for shortened link """ 
    
    result = await db.execute(
        select(ShortenedLink).where(
            ShortenedLink.short_code == short_code
        )
    )
    link = result.scalar_one_or_none()

    if not link:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="shortened link not found"
        )

    # verify user owns this link:
    if link.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="you can only view your own links"
        )

    # calculate days since creation:
    days_since = (datetime.utcnow() - link.created_at).total_seconds() / 86400

    # check if link is expired:
    is_expired = False
    if link.expires_at and link.expires_at < datetime.utcnow():
        is_expired = True

    return {
        "id": link.id,
        "short_code": link.short_code,
        "original_url": link.original_url,
        "custom_alias": link.custom_alias,
        "click_count": link.click_count,
        "created_at": link.created_at,
        "last_accessed_at": link.last_accessed_at,
        "expires_at": link.expires_at,
        "is_expired": is_expired,
        "days_since_creation": days_since
    }


@router.put("/{short_code}", response_model=ShortenedLinkResponse)
async def update_link(
    short_code: str,
    update_data: UpdateLinkRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> ShortenedLink:
    # update shortened link - only owner can update:
    
    result = await db.execute(
        select(ShortenedLink).where(
            ShortenedLink.short_code == short_code
        )
    )
    link = result.scalar_one_or_none()

    if not link:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="shortened link not found"
        )

    # verify user owns this link:
    if link.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="you can only modify your own links"
        )

    # update fields if provided:
    if update_data.original_url:
        link.original_url = update_data.original_url
    
    if update_data.expires_at:
        link.expires_at = update_data.expires_at

    db.add(link)
    await db.commit()
    await db.refresh(link)
    
    # invalidate cache after update:
    await cache.delete_link(short_code)

    return link


@router.delete("/{short_code}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_link(
    short_code: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> None:
    # delete shortened link
    # only owner can delete it:
    
    result = await db.execute(
        select(ShortenedLink).where(
            ShortenedLink.short_code == short_code
        )
    )
    link = result.scalar_one_or_none()

    if not link:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="shortened link not found"
        )

    # verify user owns this link:
    if link.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="you can only delete your own links"
        )

    await db.delete(link)
    await db.commit()
    
    # invalidate cache after delete:
    await cache.delete_link(short_code)


@router.get("/search", response_model=list[ShortenedLinkResponse])
async def search_links(
    original_url: str = Query(..., description="original url to search for"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> list[ShortenedLink]:
    
    #  search for shortened links by original url
    # only user's own links:
    result = await db.execute(
        select(ShortenedLink).where(
            and_(
                ShortenedLink.original_url.contains(original_url),
                ShortenedLink.user_id == current_user.id
            )
        ).order_by(ShortenedLink.created_at.desc())
    )
    links = result.scalars().all()

    if not links:
        return []

    return links


@router.get("/analytics/top", response_model=list[dict])
async def get_top_links(
    limit: int = Query(10, ge=1, le=100, description="number of top links to return"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> list[dict]:
    """get most accessed links from cache"""
    
    # get top links from redis cache:
    top_links = await cache.get_top_links(limit)
    
    # enrich with user's ownership info:
    result_links = []
    for item in top_links:
        result = await db.execute(
            select(ShortenedLink).where(
                ShortenedLink.short_code == item["short_code"]
            )
        )
        link = result.scalar_one_or_none()
        
        if link and link.user_id == current_user.id:
            result_links.append({
                "short_code": item["short_code"],
                "clicks": item["clicks"],
                "original_url": link.original_url,
                "created_at": link.created_at
            })
    
    return result_links

    return list(links)
