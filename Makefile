init:
	pip install -r requirements.txt

test:
	# Run unit tests
	pytest src/initial/ -vvv -s -c src/initial/pytest.ini
	pytest src/bootstrap_repository/ -vvv -s -c src/bootstrap_repository/pytest.ini
	pytest src/bootstrap_repository/deployment/lambda_codebase/initial_commit/pipelines_repository -vvv -s -c src/bootstrap_repository/deployment/lambda_codebase/initial_commit/pipelines_repository/pytest.ini
lint:
	# Linter performs static analysis to catch latent bugs
	find src/ -iname "*.py" | xargs pylint --rcfile .pylintrc 
