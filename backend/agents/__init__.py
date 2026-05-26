# =============================================================================
# ShiftIQ Agents Package
#
# This package groups the backend "agent" modules used by the FastAPI app. In
# this MVP, an agent is a focused Python module that owns one operational concern:
# loading data, creating insights, forecasting demand, generating schedules,
# simulating employee messaging, answering manager questions, or holding runtime
# state. Keeping these capabilities in a package makes the API layer thin and
# makes each workflow easier to test or replace later.
#
# The file is intentionally lightweight. Its main purpose is to mark agents/ as a
# Python package so modules can import each other with statements such as
# `from agents.data_agent import load_sales`.
# =============================================================================

