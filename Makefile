.PHONY: format lint check

format:
    @echo "🧼 Running Black..."
    black .

    @echo "🔀 Running isort..."
    isort . --profile=black --skip=env

lint:
    @echo "🔍 Running Flake8..."
    flake8 . --exclude=env

check: format lint
    @echo "✅ All checks passed."
