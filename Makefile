.PHONY: build install run-example test test-go test-python setup-python clean lint fmt help

# ── Platform detection ─────────────────────────────────────────────────────
BINARY := sagescan
ifeq ($(OS),Windows_NT)
    BINARY     := sagescan.exe
    VENV_PIP   := engine/.venv/Scripts/pip
    VENV_PYTHON:= engine/.venv/Scripts/python
    PYTHON     := python
else
    VENV_PIP   := engine/.venv/bin/pip
    VENV_PYTHON:= engine/.venv/bin/python
    PYTHON     := python3
endif

VERSION     := $(shell git describe --tags --always --dirty 2>/dev/null || echo "dev")
LDFLAGS     := -ldflags "-X main.version=$(VERSION)"
INSTALL_DIR := $(HOME)/.local/bin

# ── Build ──────────────────────────────────────────────────────────────────
build:
	@echo "🔨 Building $(BINARY) $(VERSION)..."
	go build $(LDFLAGS) -o $(BINARY) ./cmd/sagescan/main.go
	@echo "✅ Binary ready: ./$(BINARY)"

# ── Install globally (no sudo) ─────────────────────────────────────────────
install: build
	@mkdir -p $(INSTALL_DIR)
	@cp $(BINARY) $(INSTALL_DIR)/$(BINARY)
	@echo "✅ Installed to $(INSTALL_DIR)/$(BINARY)"
	@echo "   Add to PATH: echo 'export PATH=\"\$$HOME/.local/bin:\$$PATH\"' >> ~/.zshrc && source ~/.zshrc"

# ── Python environment ─────────────────────────────────────────────────────
setup-python:
	@echo "🐍 Creating Python virtual environment..."
	$(PYTHON) -m venv engine/.venv
	$(VENV_PYTHON) -m pip install --upgrade pip
	$(VENV_PIP) install -r engine/requirements.txt
	$(VENV_PIP) install pytest pytest-cov
	@echo "✅ Python environment ready: engine/.venv"
	@echo "   Add venv python to PATH or set SAGESCAN_ENGINE_PYTHON=engine/.venv/Scripts/python"

# ── Data folder ────────────────────────────────────────────────────────────
data-dir:
	@mkdir -p examples/data
	@echo "✅ examples/data/ created"

# ── Download datasets ──────────────────────────────────────────────────────
download-titanic: data-dir
	@echo "📥 Downloading Titanic dataset..."
	curl -L -o examples/data/titanic.csv \
	  "https://raw.githubusercontent.com/datasciencedojo/datasets/master/titanic.csv"
	@echo "✅ Saved to examples/data/titanic.csv"
	@wc -l examples/data/titanic.csv

download-airbnb: data-dir
	@echo "📥 Downloading Airbnb NYC listings..."
	curl -L -o examples/data/airbnb_listings.csv \
	  "https://data.insideairbnb.com/united-states/ny/new-york-city/2024-09-04/visualisations/listings.csv"
	@echo "✅ Saved to examples/data/airbnb_listings.csv"
	@wc -l examples/data/airbnb_listings.csv

download-all: download-titanic download-airbnb
	@echo "✅ All datasets downloaded"

# ── Run examples ───────────────────────────────────────────────────────────
run-titanic: build
	@echo "▶️  Validating Titanic dataset..."
	./$(BINARY) validate examples/rules/titanic_rules.yaml

run-airbnb: build
	@echo "▶️  Validating Airbnb NYC listings..."
	./$(BINARY) validate examples/rules/airbnb_rules.yaml

run-example: build
	./$(BINARY) validate examples/basic_rules.yaml

# ── Tests ──────────────────────────────────────────────────────────────────
test-go:
	@echo "🧪 Running Go tests..."
	go test -v -race ./...

test-python:
	@echo "🧪 Running Python tests..."
	cd engine && $(VENV_PYTHON) -m pytest \
	  sagescan_engine/validators/test_implementations.py \
	  sagescan_engine/rules/test_models.py \
	  -v --tb=short

test: test-go test-python
	@echo "✅ All tests passed"

# ── Code quality ───────────────────────────────────────────────────────────
lint:
	@echo "🔍 Linting Go..."
	go vet ./...
	@echo "🔍 Linting Python..."
	$(VENV_PYTHON) -m py_compile engine/sagescan_engine/core/pipeline.py \
	  engine/sagescan_engine/core/runner.py \
	  engine/sagescan_engine/validators/implementations.py \
	  engine/main.py && echo "Python syntax OK"

fmt:
	@echo "✨ Formatting Go..."
	gofmt -w .

# ── Clean ──────────────────────────────────────────────────────────────────
clean:
	@rm -f $(BINARY) sagescan.exe
	@find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	@echo "🧹 Clean done"

# ── Help ───────────────────────────────────────────────────────────────────
help:
	@echo ""
	@echo "SageScan — Data Quality Validation Tool"
	@echo ""
	@echo "  make build              Build the CLI binary"
	@echo "  make install            Install to ~/.local/bin"
	@echo "  make setup-python       Create venv + install Python deps"
	@echo "  make data-dir           Create examples/data/ folder"
	@echo "  make download-titanic   Download Titanic CSV"
	@echo "  make download-airbnb    Download Airbnb NYC CSV"
	@echo "  make download-all       Download all datasets"
	@echo "  make run-titanic        Validate Titanic dataset"
	@echo "  make run-airbnb         Validate Airbnb dataset"
	@echo "  make test               Run all Go + Python tests"
	@echo "  make test-go            Run Go tests only"
	@echo "  make test-python        Run Python tests only"
	@echo "  make lint               Lint Go + Python"
	@echo "  make fmt                Format Go code"
	@echo "  make clean              Remove build artefacts"
	@echo ""

.DEFAULT_GOAL := help
