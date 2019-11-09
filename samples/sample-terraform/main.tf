provider "aws" {
  version = "~> 2.0"
  assume_role {
    role_arn     = "arn:aws:iam::${var.TARGET_ACCOUNT_ID}:role/${var.TARGET_ACCOUNT_ROLE}"
  }
}

resource "aws_s3_bucket" "b" {
  bucket = "${var.my_bucket_name}"
  acl    = "private"

  tags = {
    Name        = "My bucket"
    Environment = "Dev"
  }
}