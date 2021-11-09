resource "aws_s3_bucket" "s3" {
  bucket = "my-tf-test-bucket-${var.TARGET_REGION}-${var.TARGET_ACCOUNT_ID}"
  acl    = "private"
}

resource "aws_s3_bucket_public_access_block" "s3-public-block" {
  bucket = aws_s3_bucket.s3.id

  block_public_acls   = true
  block_public_policy = true
}
