resource "aws_s3_bucket" "b" {
  bucket = "my-tf-test-bucket-${var.TARGET_REGION}-${var.TARGET_ACCOUNT_ID}"
  acl    = "private"
}
