"""
Security Rule Engine.
"""
# Import these to trigger the RuleRegistry decorators
import app.rules.s3
import app.rules.iam
import app.rules.ec2
import app.rules.security_groups
import app.rules.rds
import app.rules.cloudtrail
