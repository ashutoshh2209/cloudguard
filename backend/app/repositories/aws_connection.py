from typing import Optional
from sqlalchemy.orm import Session
from app.models.aws_connection import AWSConnection

class AWSConnectionRepository:
    def get_by_account(self, db: Session, account_id: str) -> Optional[AWSConnection]:
        return db.query(AWSConnection).filter(AWSConnection.account_id == account_id).first()

    def get_active(self, db: Session) -> Optional[AWSConnection]:
        # Simple for now, return the first one
        return db.query(AWSConnection).first()

    def create(self, db: Session, account_id: str, role_arn: str, region: str) -> AWSConnection:
        conn = AWSConnection(
            account_id=account_id,
            role_arn=role_arn,
            region=region,
            status="verified"
        )
        db.add(conn)
        db.flush()
        return conn

    def update_status(self, db: Session, account_id: str, status: str):
        conn = self.get_by_account(db, account_id)
        if conn:
            conn.status = status
            db.flush()

aws_connection_repo = AWSConnectionRepository()
