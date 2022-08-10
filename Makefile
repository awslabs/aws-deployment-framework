init:
	pip install -r requirements.txt

test:
	# Run unit tests
	pytest src/lambda_codebase/account -vvv -s -c src/lambda_codebase/account/pytest.ini
	pytest src/lambda_codebase/account_processing -vvv -s -c src/lambda_codebase/account_processing/pytest.ini
	pytest src/lambda_codebase/initial_commit/bootstrap_repository -vvv -s -c src/lambda_codebase/initial_commit/bootstrap_repository/pytest.ini
	pytest src/lambda_codebase/initial_commit/bootstrap_repository/adf-bootstrap/deployment/lambda_codebase -vvv -s -c src/lambda_codebase/initial_commit/bootstrap_repository/adf-bootstrap/deployment/lambda_codebase/pytest.ini
	pytest src/lambda_codebase/initial_commit/bootstrap_repository/adf-build/shared/python -vvv -s -c src/lambda_codebase/initial_commit/bootstrap_repository/adf-build/shared/python/pytest.ini
	pytest src/lambda_codebase/initial_commit/bootstrap_repository/adf-build/shared/cdk -vvv -s -c src/lambda_codebase/initial_commit/bootstrap_repository/adf-build/shared/cdk/pytest.ini
	pytest src/lambda_codebase/initial_commit/bootstrap_repository/adf-build/shared -vvv -s -c src/lambda_codebase/initial_commit/bootstrap_repository/adf-build/shared/pytest.ini
lint:
	# Linter performs static analysis to catch latent bugs
	find src/ -iname "*.py" -not -path "src/.aws-sam/*" | xargs pylint --rcfile .pylintrc
	cfn-lint

build:
	sam build -u

deploy:
	sam deploy --capabilities CAPABILITY_NAMED_IAM CAPABILITY_AUTO_EXPAND
