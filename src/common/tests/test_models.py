from datetime import date
from typing import Any

import pytest
from pydantic import ValidationError

from src.common.models import Applicant


def test_applicant_valid_serialization() -> None:
    data: dict[str, Any] = {
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
    applicant = Applicant(**data)
    assert applicant.annual_inc == 85000.0
    assert applicant.addr_state == "CA"


def test_applicant_invalid_income() -> None:
    with pytest.raises(ValidationError):
        Applicant(
            annual_inc=-500.0,  # Invalid: must be gt=0
            home_ownership="OWN",
            addr_state="TX",
            dti=10.0,
            earliest_cr_line=date(2015, 1, 1),
            open_acc=5,
            revol_bal=1000.0,
            revol_util=50.0,
            total_acc=10,
        )
