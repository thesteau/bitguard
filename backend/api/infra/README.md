# EC2 Terraform

This folder provisions a single Ubuntu EC2 instance, a security group, and an optional EC2 key pair.

## What it assumes

- You are using the default VPC and one of its default subnets in the selected AWS region.
- AWS credentials are provided through environment variables, not Terraform variables.
- Instance settings are provided through `TF_VAR_*` environment variables.

## Files

- `ec2_setup.tf`: Terraform configuration for the EC2 instance.
- `.env.example`: Example environment file for AWS credentials and Terraform variables.

## PowerShell usage

1. Copy `.env.example` to `.env` and fill in real values.
2. Load the file into the current PowerShell session:

```powershell
Get-Content .env | ForEach-Object {
    if ($_ -match '^\s*#' -or $_ -match '^\s*$') { return }
    $name, $value = $_ -split '=', 2
    [System.Environment]::SetEnvironmentVariable($name, $value)
}
```

3. Run Terraform:

```powershell
terraform init
terraform plan
terraform apply
```

## Notes

- `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY` stay out of Terraform state when passed as environment variables.
- `TF_VAR_ssh_public_key` should be the full public key contents from your local machine.
- If your AWS account does not have a default VPC in the target region, this configuration will fail and you will need explicit networking resources.
