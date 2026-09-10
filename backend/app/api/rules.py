from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.database_models import Rule
from app.rules.repository import RuleRepository
from app.schemas.pydantic_schemas import RuleItem

router = APIRouter(prefix="/api/rules", tags=["Legal Metrology Rules"])

repo = RuleRepository()

@router.get("", response_model=List[RuleItem])
def get_rules(db: Session = Depends(get_db)):
    rules = db.query(Rule).all()
    if not rules:
        # Fallback to static rule repository
        static_rules = repo.get_all_rules()
        return static_rules
    return rules

@router.get("/{rule_id}")
def get_rule_by_id(rule_id: str, db: Session = Depends(get_db)):
    rule = db.query(Rule).filter(Rule.id == rule_id).first()
    if not rule:
        rule = db.query(Rule).filter(Rule.rule_code == rule_id).first()
    
    if not rule:
        static_rule = repo.get_rule_by_code(rule_id)
        if static_rule:
            return static_rule
        raise HTTPException(status_code=404, detail="Rule not found")
    
    return rule
