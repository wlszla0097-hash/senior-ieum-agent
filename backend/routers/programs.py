"""routers/programs.py — 사업 목록 창구: 프론트 탭·모드·빠른 질문·도구 이름을 registry 에서 그대로 내려준다."""
from fastapi import APIRouter
from programs import registry

router = APIRouter(prefix="/api/programs", tags=["programs"])


@router.get("")
def list_programs():
    """등록된 사업(탭) 목록. 새 사업은 programs/registry.py 에 추가하면 여기 자동 반영."""
    return registry.list_programs()
