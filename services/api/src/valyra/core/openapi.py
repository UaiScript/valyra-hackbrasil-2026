"""OperationIds estáveis; o nome explícito da rota é parte do contrato."""

from fastapi.routing import APIRoute


def operation_id(route: APIRoute) -> str:
    return route.name
