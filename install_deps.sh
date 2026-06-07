#!/bin/bash
echo "Installing Python packages..."
pip install fastapi uvicorn sqlalchemy python-jose passlib python-multipart ccxt pandas scikit-learn xgboost
echo "DONE: $?"
