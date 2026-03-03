from typing import List
import numpy as np

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, delete, func
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from domain.models import User, UserRequests
from schemas.schemas import RequestResponse, StatsResponse
from auth.dependencies import get_current_user, get_admin_user


router = APIRouter(
    prefix="/history",
    tags=["Requests History"]
)


@router.get(
    "",
    response_model=List[RequestResponse],
    summary="Get all requests from all users",
    description="Retrieve all requests from the database"
)
async def get_requests(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> List[UserRequests]:
    """
    Get user requests, written as analog of thee function to get users
    """
    result = await db.execute(
        select(UserRequests)
        .where(UserRequests.user_id == current_user.id)
        .order_by(UserRequests.timestamp.desc())
        .offset(skip)
        .limit(limit)
    )
    requests = result.scalars().all()
    return list(requests)


@router.get("/stats", response_model=StatsResponse)
async def get_requests_statistics(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_admin_user)
):
    try:
        result = await db.execute(
            select(
                UserRequests.processing_time_ms,
                UserRequests.text_length,
                UserRequests.prediction
            ).where(UserRequests.processing_time_ms.is_not(None))
        )
        
        data = result.fetchall()
        
        if not data:
            return StatsResponse(
                total_requests=0,
                avg_processing_time_ms=0.0,
                processing_time_quantiles={
                    "mean": 0.0,
                    "50%": 0.0,
                    "95%": 0.0,
                    "99%": 0.0,
                    "min": 0.0,
                    "max": 0.0,
                    "std": 0.0
                },
                text_characteristics={
                    "avg_length": 0.0,
                    "min_length": 0,
                    "max_length": 0,
                    "std_length": 0.0
                },
                prediction_distribution={
                    "toxic": 0,
                    "non_toxic": 0,
                    "toxic_percentage": 0.0
                }
            )
        
        processing_times = np.array([row[0] for row in data if row[0] is not None])
        text_lengths = np.array([row[1] for row in data if row[1] is not None])
        predictions = [row[2] for row in data]
        toxic_count = sum(1 for p in predictions if p == 1)
        non_toxic_count = len(predictions) - toxic_count
        
        return StatsResponse(
            total_requests=len(data),
            avg_processing_time_ms=float(np.mean(processing_times)),
            processing_time_quantiles={
                "mean": float(np.mean(processing_times)),
                "50%": float(np.percentile(processing_times, 50)),
                "95%": float(np.percentile(processing_times, 95)),
                "99%": float(np.percentile(processing_times, 99)),
                "min": float(np.min(processing_times)),
                "max": float(np.max(processing_times)),
                "std": float(np.std(processing_times))
            },
            text_characteristics={
                "avg_length": float(np.mean(text_lengths)),
                "min_length": int(np.min(text_lengths)),
                "max_length": int(np.max(text_lengths)),
                "std_length": float(np.std(text_lengths))
            },
            prediction_distribution={
                "toxic": toxic_count,
                "non_toxic": non_toxic_count,
                "toxic_percentage": round((toxic_count / len(predictions)) * 100, 2) if predictions else 0.0
            }
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting statistics: {str(e)}"
        )


@router.delete("")
async def delete_requests_history(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_admin_user)
):
    try:
        result = await db.execute(delete(UserRequests))
        await db.commit()
        
        return {
            "message": "History deleted successfully",
            "deleted_count": result.rowcount
        }
        
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deleting history: {str(e)}"
        )
