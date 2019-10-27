init:
	pip install -r requirements.txt
	pip install -r src/lambda_codebase/initial_commit/requirements.txt

test:
	# Run unit tests
	pytest src/lambda_codebase/initial_commit/bootstrap_repository -vvv -s -c src/lambda_codebase/initial_commit/bootstrap_repository/pytest.ini
	pytest src/lambda_codebase/initial_commit/bootstrap_repository/deployment/lambda_codebase -vvv -s -c src/lambda_codebase/initial_commit/bootstrap_repository/deployment/lambda_codebase/pytest.ini
	pytest src/lambda_codebase/initial_commit/bootstrap_repository/adf-build/shared/python -vvv -s -c src/lambda_codebase/initial_commit/bootstrap_repository/adf-build/shared/python/pytest.ini
	pytest src/lambda_codebase/initial_commit/bootstrap_repository/adf-build/shared -vvv -s -c src/lambda_codebase/initial_commit/bootstrap_repository/adf-build/shared/pytest.ini
	pytest src/lambda_codebase/initial_commit -vvv -s -c src/lambda_codebase/initial_commit/pytest.ini
lint:
	# Linter performs static analysis to catch latent bugs
	find src/ -iname "*.py" | xargs pylint --rcfile .pylintrc
  