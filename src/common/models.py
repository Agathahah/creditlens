from datetime import date
from enum import StrEnum

from pydantic import BaseModel, EmailStr, Field


class LoanStatus(StrEnum):
    FULLY_PAID = "Fully Paid"
    CHARGED_OFF = "Charged Off"
    CURRENT = "Current"
    DEFAULT = "Default"
    LATE_31_120 = "Late (31-120 days)"
    LATE_16_30 = "Late (16-30 days)"


class Grade(StrEnum):
    A = "A"
    B = "B"
    C = "C"
    D = "D"
    E = "E"
    F = "F"
    G = "G"


class RiskTier(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class EmploymentStability(StrEnum):
    STABLE = "stable"
    MODERATE = "moderate"
    UNSTABLE = "unstable"
    UNKNOWN = "unknown"


class Applicant(BaseModel):
    """Pydantic model representing a credit scoring applicant."""

    applicant_id: str | None = Field(default=None, description="Unique identifier of the applicant")
    email: EmailStr | None = Field(default=None, description="Email address of the applicant")
    annual_inc: float = Field(
        ..., gt=0, description="Annual income of the applicant in USD", examples=[75000.0]
    )
    emp_length: str | None = Field(
        default=None,
        description="Employment length in years (e.g. '10+ years', '< 1 year')",
        examples=["10+ years"],
    )
    home_ownership: str = Field(
        ..., description="Home ownership status (RENT, OWN, MORTGAGE)", examples=["RENT"]
    )
    addr_state: str = Field(
        ..., min_length=2, max_length=2, description="Two-letter US state code", examples=["NY"]
    )
    dti: float = Field(..., ge=0, description="Debt-to-income ratio (percentage)", examples=[15.5])
    delinq_2yrs: int = Field(
        default=0,
        ge=0,
        description="Number of 30+ days delinquency events in past 2 years",
        examples=[0],
    )
    earliest_cr_line: date = Field(..., description="Date of earliest opened credit line")
    open_acc: int = Field(..., ge=0, description="Number of open credit accounts", examples=[8])
    revol_bal: float = Field(
        ..., ge=0, description="Total revolving credit balance in USD", examples=[12000.5]
    )
    revol_util: float = Field(
        ...,
        ge=0,
        le=100,
        description="Revolving line utilization rate (percentage)",
        examples=[35.2],
    )
    total_acc: int = Field(
        ..., ge=0, description="Total number of credit lines on file", examples=[15]
    )

    model_config = {
        "use_enum_values": True,
        "json_schema_extra": {
            "example": {
                "annual_inc": 85000.0,
                "emp_length": "10+ years",
                "home_ownership": "MORTGAGE",
                "addr_state": "CA",
                "dti": 12.3,
                "delinq_2yrs": 0,
                "earliest_cr_line": "2010-06-15",
                "open_acc": 10,
                "revol_bal": 15000.0,
                "revol_util": 42.1,
                "total_acc": 22,
            }
        },
    }


class LoanApplication(BaseModel):
    """Pydantic model representing a credit loan application."""

    loan_id: str | None = Field(default=None, description="Unique identifier of the loan")
    applicant: Applicant = Field(..., description="Applicant personal and credit details")
    loan_amnt: float = Field(
        ..., gt=0, description="Requested loan amount in USD", examples=[15000.0]
    )
    term: str = Field(
        ..., description="Loan repayment term (e.g. '36 months', '60 term')", examples=["36 months"]
    )
    purpose: str = Field(
        ...,
        description="Purpose of the loan (e.g. debt_consolidation, major_purchase)",
        examples=["debt_consolidation"],
    )


class CounterfactualResult(BaseModel):
    """Pydantic model for counterfactual recommendations."""

    parameter: str = Field(..., description="Name of the parameter that needs to change")
    current_value: str = Field(..., description="Current value of the parameter")
    target_value: str = Field(..., description="Target value required for approval recommendation")


class ScoreResult(BaseModel):
    """Pydantic model representing the output of a credit score evaluation."""

    score_id: str = Field(..., description="Unique transaction ID for this score evaluation")
    risk_score: float = Field(
        ..., ge=0, le=1, description="Probability of default (risk score)", examples=[0.12]
    )
    risk_tier: RiskTier = Field(..., description="Assigned risk tier (low, medium, high)")
    approved: bool = Field(
        ..., description="Automatic decision recommendation based on cutoff thresholds"
    )
    explainability: dict[str, float] | None = Field(
        default=None, description="SHAP feature attribution weights map"
    )
    counterfactuals: list[CounterfactualResult] = Field(
        default_factory=list, description="Suggestions to improve decision outcome"
    )
