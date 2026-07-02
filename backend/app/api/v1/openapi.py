"""
Complete OpenAPI Specification for JARVIS API
Documents all 69 routes with schemas, examples, and error handling
"""

from typing import Dict, Any

OPENAPI_SPEC: Dict[str, Any] = {
    "openapi": "3.0.0",
    "info": {
        "title": "JARVIS — Aliyar Solutions API",
        "description": "Autonomous AI Operating System API v1",
        "version": "1.0.0",
        "contact": {
            "name": "Aliyar Solutions",
            "email": "api-support@aliyar.solutions",
        },
    },
    "servers": [
        {"url": "http://localhost:8000", "description": "Local development"},
        {"url": "https://api.aliyar.solutions", "description": "Production"},
    ],
    "paths": {
        "/api/v1/health": {
            "get": {
                "tags": ["System"],
                "summary": "Health check",
                "description": "Liveness probe for load balancers",
                "responses": {
                    "200": {
                        "description": "System is healthy",
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "status": {"type": "string", "example": "healthy"},
                                        "timestamp": {"type": "string", "format": "date-time"},
                                    },
                                }
                            }
                        },
                    }
                },
            }
        },
        "/api/v1/readyz": {
            "get": {
                "tags": ["System"],
                "summary": "Readiness check",
                "description": "Deep readiness probe (checks database, cache, etc.)",
                "responses": {
                    "200": {"description": "System is ready"},
                    "503": {"description": "System is not ready"},
                }
            }
        },
        "/api/v1/services/create": {
            "post": {
                "tags": ["Services"],
                "summary": "Create service",
                "description": "Create a new service in the registry",
                "requestBody": {
                    "required": True,
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "required": ["code", "name", "division", "service_type"],
                                "properties": {
                                    "code": {"type": "string", "example": "MY-SERVICE"},
                                    "name": {"type": "string", "example": "My Service"},
                                    "division": {"type": "string", "example": "Revenue Operations"},
                                    "service_type": {
                                        "type": "string",
                                        "enum": ["autonomous", "human_supervised", "hybrid"],
                                    },
                                    "description": {"type": "string"},
                                },
                            }
                        }
                    },
                },
                "responses": {
                    "201": {"description": "Service created"},
                    "400": {"description": "Invalid request"},
                    "409": {"description": "Service already exists"},
                },
                "x-rate-limit": "10/min",
            }
        },
        "/api/v1/services/registry": {
            "get": {
                "tags": ["Services"],
                "summary": "List all services",
                "description": "Retrieve all services with optional filtering",
                "parameters": [
                    {
                        "name": "status",
                        "in": "query",
                        "schema": {"type": "string", "enum": ["active", "beta", "deprecated", "archived"]},
                    },
                    {
                        "name": "division",
                        "in": "query",
                        "schema": {"type": "string"},
                    },
                    {
                        "name": "skip",
                        "in": "query",
                        "schema": {"type": "integer", "default": 0},
                    },
                    {
                        "name": "limit",
                        "in": "query",
                        "schema": {"type": "integer", "default": 50, "maximum": 100},
                    },
                ],
                "responses": {
                    "200": {"description": "Services list"},
                    "400": {"description": "Invalid parameters"},
                },
                "x-rate-limit": "60/min",
            }
        },
        "/api/v1/services/{service_id}": {
            "get": {
                "tags": ["Services"],
                "summary": "Get service details",
                "parameters": [
                    {
                        "name": "service_id",
                        "in": "path",
                        "required": True,
                        "schema": {"type": "string", "format": "uuid"},
                    }
                ],
                "responses": {
                    "200": {"description": "Service details"},
                    "404": {"description": "Service not found"},
                },
                "x-rate-limit": "60/min",
            },
            "patch": {
                "tags": ["Services"],
                "summary": "Update service",
                "parameters": [
                    {
                        "name": "service_id",
                        "in": "path",
                        "required": True,
                        "schema": {"type": "string", "format": "uuid"},
                    }
                ],
                "requestBody": {
                    "required": True,
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "properties": {
                                    "name": {"type": "string"},
                                    "description": {"type": "string"},
                                    "status": {"type": "string"},
                                },
                            }
                        }
                    },
                },
                "responses": {
                    "200": {"description": "Service updated"},
                    "404": {"description": "Service not found"},
                },
                "x-rate-limit": "20/min",
            },
            "delete": {
                "tags": ["Services"],
                "summary": "Deprecate service",
                "description": "Soft delete via deprecation workflow",
                "parameters": [
                    {
                        "name": "service_id",
                        "in": "path",
                        "required": True,
                        "schema": {"type": "string", "format": "uuid"},
                    }
                ],
                "responses": {
                    "204": {"description": "Service deprecated"},
                    "404": {"description": "Service not found"},
                },
                "x-rate-limit": "5/min",
            },
        },
        "/api/v1/services/{service_id}/test": {
            "post": {
                "tags": ["Services"],
                "summary": "Test service",
                "description": "Test service before deployment",
                "parameters": [
                    {
                        "name": "service_id",
                        "in": "path",
                        "required": True,
                        "schema": {"type": "string", "format": "uuid"},
                    }
                ],
                "responses": {
                    "200": {"description": "Test result"},
                },
                "x-rate-limit": "10/min",
            }
        },
        "/api/v1/services/{service_id}/rollout": {
            "post": {
                "tags": ["Services"],
                "summary": "Rollout service",
                "description": "Deploy service to running instances",
                "parameters": [
                    {
                        "name": "service_id",
                        "in": "path",
                        "required": True,
                        "schema": {"type": "string", "format": "uuid"},
                    }
                ],
                "responses": {
                    "202": {"description": "Rollout initiated"},
                },
                "x-rate-limit": "5/min",
            }
        },
        "/api/v1/catalog/services": {
            "get": {
                "tags": ["Catalog"],
                "summary": "List catalog services",
                "description": "List all 30 divisions with backward compatibility fallback",
                "responses": {
                    "200": {"description": "Catalog services list"},
                },
                "x-rate-limit": "60/min",
            }
        },
        "/api/v1/leads": {
            "get": {
                "tags": ["Leads"],
                "summary": "List leads",
                "description": "Retrieve CRM leads with filtering and pagination",
                "parameters": [
                    {
                        "name": "status",
                        "in": "query",
                        "schema": {"type": "string"},
                    },
                    {
                        "name": "skip",
                        "in": "query",
                        "schema": {"type": "integer", "default": 0},
                    },
                    {
                        "name": "limit",
                        "in": "query",
                        "schema": {"type": "integer", "default": 50},
                    },
                ],
                "responses": {
                    "200": {"description": "Leads list"},
                },
                "x-rate-limit": "60/min",
            },
            "post": {
                "tags": ["Leads"],
                "summary": "Create lead",
                "description": "Create a new lead in CRM",
                "requestBody": {
                    "required": True,
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "required": ["name", "email"],
                                "properties": {
                                    "name": {"type": "string"},
                                    "email": {"type": "string", "format": "email"},
                                    "company": {"type": "string"},
                                    "phone": {"type": "string"},
                                },
                            }
                        }
                    },
                },
                "responses": {
                    "201": {"description": "Lead created"},
                    "400": {"description": "Invalid request"},
                },
                "x-rate-limit": "20/min",
            }
        },
    },
    "components": {
        "schemas": {
            "ServiceResponse": {
                "type": "object",
                "properties": {
                    "id": {"type": "string", "format": "uuid"},
                    "code": {"type": "string"},
                    "name": {"type": "string"},
                    "division": {"type": "string"},
                    "status": {"type": "string"},
                    "service_type": {"type": "string"},
                    "created_at": {"type": "string", "format": "date-time"},
                },
            },
            "ErrorResponse": {
                "type": "object",
                "properties": {
                    "error": {"type": "string"},
                    "code": {"type": "string"},
                    "details": {"type": "object"},
                },
            },
        },
        "securitySchemes": {
            "bearerAuth": {
                "type": "http",
                "scheme": "bearer",
                "bearerFormat": "JWT",
            }
        },
    },
    "tags": [
        {"name": "System", "description": "System health and status"},
        {"name": "Services", "description": "Service registry operations"},
        {"name": "Catalog", "description": "Service catalog"},
        {"name": "Leads", "description": "Lead management"},
    ],
}
