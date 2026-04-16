# /app/backend/routes/__init__.py
# Módulo de rutas - Exporta funciones auxiliares compartidas

from routes.auth import (
    router as auth_router,
    users_router,
    get_current_user,
    require_permission,
    hash_password,
    verify_password,
    create_token,
    UserLogin,
    UserCreate,
    UserUpdate,
    UserResponse,
    TokenResponse
)

from routes.expenses import (
    router as expenses_router,
    get_next_expense_number,
    update_expense_amounts,
    check_overdue_expenses,
    ExpenseBase,
    ExpenseCreate,
    ExpenseUpdate,
    ExpenseResponse,
    ExpenseListResponse
)

__all__ = [
    # Routers
    'auth_router',
    'users_router',
    'expenses_router',
    
    # Auth helpers
    'get_current_user',
    'require_permission',
    'hash_password',
    'verify_password',
    'create_token',
    
    # Auth models
    'UserLogin',
    'UserCreate',
    'UserUpdate',
    'UserResponse',
    'TokenResponse',
    
    # Expense helpers
    'get_next_expense_number',
    'update_expense_amounts',
    'check_overdue_expenses',
    
    # Expense models
    'ExpenseBase',
    'ExpenseCreate',
    'ExpenseUpdate',
    'ExpenseResponse',
    'ExpenseListResponse'
]
