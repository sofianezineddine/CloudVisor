"""CloudFormation template for AWS onboarding."""

AWS_CLOUDFORMATION_TEMPLATE = """AWSTemplateFormatVersion: '2010-09-09'
Description: CloudVisor Read-Only Access Role - Creates an IAM role that allows CloudVisor to scan your AWS account

Metadata:
  AWS::CloudFormation::Interface:
    ParameterGroups:
      - Label:
          default: "CloudVisor Configuration"
        Parameters:
          - CloudVisorAccountId
          - ExternalId
    ParameterLabels:
      CloudVisorAccountId:
        default: "CloudVisor AWS Account ID"
      ExternalId:
        default: "External ID (for security)"

Parameters:
  CloudVisorAccountId:
    Type: String
    Description: "Your CloudVisor AWS account ID (12 digits)"
    AllowedPattern: "^\\d{12}$"
    ConstraintDescription: "Must be a 12-digit AWS account ID"

  ExternalId:
    Type: String
    Description: "Unique external ID for added security (provided by CloudVisor)"
    MinLength: 4
    MaxLength: 1224

Resources:
  CloudVisorReadOnlyRole:
    Type: AWS::IAM::Role
    Properties:
      RoleName: CloudVisorReadOnly
      Description: "Read-only role for CloudVisor security scanning"
      AssumeRolePolicyDocument:
        Version: '2012-10-17'
        Statement:
          - Effect: Allow
            Principal:
              AWS: !Sub "arn:aws:iam::${CloudVisorAccountId}:root"
            Action: sts:AssumeRole
            Condition:
              StringEquals:
                sts:ExternalId: !Ref ExternalId
      ManagedPolicyArns:
        - arn:aws:iam::aws:policy/ReadOnlyAccess
        - arn:aws:iam::aws:policy/job-function/SupportUser
      Tags:
        - Key: ManagedBy
          Value: CloudVisor
        - Key: Purpose
          Value: SecurityScanning

Outputs:
  RoleArn:
    Description: "ARN of the CloudVisor Read-Only Role"
    Value: !GetAtt CloudVisorReadOnlyRole.Arn
    Export:
      Name: CloudVisorReadOnlyRoleArn

  ExternalId:
    Description: "External ID used for this role"
    Value: !Ref ExternalId
"""


def get_aws_onboarding_template(cloudvisor_account_id: str, external_id: str) -> str:
    """Get CloudFormation template with user-specific values."""
    return AWS_CLOUDFORMATION_TEMPLATE.replace(
        "CloudVisorAccountId: Your CloudVisor AWS Account ID",
        f"CloudVisorAccountId: {cloudvisor_account_id}"
    ).replace(
        "ExternalId: Your External ID",
        f"ExternalId: {external_id}"
    )
