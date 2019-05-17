init:
	pip install -r requirements.txt

test:
	# Run unit tests
	pytest src/lambda_codebase/initial_commit/bootstrap_repository -vvv -s -c src/lambda_codebase/initial_commit/bootstrap_repository/pytest.ini
	pytest src/lambda_codebase/initial_commit/bootstrap_repository/deployment/lambda_codebase -vvv -s -c src/lambda_codebase/initial_commit/bootstrap_repository/deployment/lambda_codebase/pytest.ini
	pytest src/lambda_codebase/initial_commit/bootstrap_repository/deployment/lambda_codebase/initial_commit/pipelines_repository -vvv -s -c src/lambda_codebase/initial_commit/bootstrap_repository/deployment/lambda_codebase/initial_commit/pipelines_repository/pytest.ini
lint:
	# Linter performs static analysis to catch latent bugs
	find src/ -iname "*.py" | xargs pylint --rcfile .pylintrc 
