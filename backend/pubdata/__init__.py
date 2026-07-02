"""공공데이터 연계 패키지.

여러 공공데이터셋을 "설정(레지스트리)만 추가하면" 늘릴 수 있도록,
개별 API 하드코딩 대신 다음 계층으로 분리한다.

    registry.py  데이터셋 = 설정 한 개 (도메인·제공기관·엔드포인트·매핑·시드)
    adapters.py  제각각인 API/CSV 응답 → 공통 스키마 {차원, 키, 값}
    store.py     SQLite 통합 저장소 (수집 결과 캐시 + 통합 조회)
    ingest.py    데이터셋별 수집: 키 있으면 실 API, 없으면 시드로 적재
    service.py   키워드 → 도메인 매칭 → 통계 시리즈 + 관련 데이터셋 목록

프론트/서비스 계약(datasets/stats)은 고정이라, 실데이터로 바꿔도 UI는 그대로.
"""

from . import ingest, registry, service, store

__all__ = ["ingest", "registry", "service", "store"]
