"""schemas package — request / response DTOs."""
from app.schemas.analytics import (
    CareerStabilityResponse,
    DnaReasonCode,
    EmergencyPillar,
    EmergencyResponse,
    ExplainResponse,
    FraudResponse,
    FraudSignalItem,
    GoalsRequest,
    GoalsResponse,
    HiddenCounterpartyItem,
    HiddenIncomeResponse,
    HiddenSourceItem,
    IncomeShockMonth,
    IncomeShockRequest,
    IncomeShockResponse,
    PlatformRiskItem,
    PlatformRiskResponse,
    TimelineEvent,
    TimelineResponse,
)
from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse, UserResponse
from app.schemas.identity import IdentityResponse, PermissionsResponse
from app.schemas.onboarding import (
    BankAccountIn,
    GigPlatformIn,
    IncomeSourceIn,
    OnboardingProgress,
    PersonalDetailsIn,
    UPIAppIn,
)
from app.schemas.scoring import (
    DnaResponse,
    IncomeQualityResponse,
    TwinSimulateRequest,
    TwinSimulateResponse,
    AnomalyScoreRequest,
    AnomalyScoreResponse,
)

__all__ = [
    # auth
    "LoginRequest",
    "RegisterRequest",
    "TokenResponse",
    "UserResponse",
    # identity
    "IdentityResponse",
    "PermissionsResponse",
    # onboarding
    "BankAccountIn",
    "GigPlatformIn",
    "IncomeSourceIn",
    "OnboardingProgress",
    "PersonalDetailsIn",
    "UPIAppIn",
    # scoring
    "DnaResponse",
    "IncomeQualityResponse",
    "TwinSimulateRequest",
    "TwinSimulateResponse",
    "AnomalyScoreRequest",
    "AnomalyScoreResponse",

    # analytics
    "CareerStabilityResponse",
    "DnaReasonCode",
    "EmergencyPillar",
    "EmergencyResponse",
    "ExplainResponse",
    "FraudResponse",
    "FraudSignalItem",
    "GoalsRequest",
    "GoalsResponse",
    "HiddenCounterpartyItem",
    "HiddenIncomeResponse",
    "HiddenSourceItem",
    "IncomeShockMonth",
    "IncomeShockRequest",
    "IncomeShockResponse",
    "PlatformRiskItem",
    "PlatformRiskResponse",
    "TimelineEvent",
    "TimelineResponse",
]
