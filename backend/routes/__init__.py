# /app/backend/routes/__init__.py
# Módulo de rutas - Exporta routers y funciones auxiliares compartidas

# ==================== FASE 1 ====================
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
    update_expense_amounts as expenses_update_amounts,
    check_overdue_expenses as expenses_check_overdue,
    ExpenseBase,
    ExpenseCreate,
    ExpenseUpdate,
    ExpenseResponse,
    ExpenseListResponse
)

# ==================== FASE 2 ====================
from routes.payments import (
    router as payments_router,
    update_expense_amounts as payments_update_amounts,
    PaymentBase,
    PaymentCreate,
    PaymentResponse,
    PaymentListResponse
)

from routes.dashboard import (
    router as dashboard_router,
    check_overdue_expenses as dashboard_check_overdue,
    TypeBreakdown,
    DashboardSummary,
    MonthlyChartItem,
    AlertResponse,
    UpcomingPayments
)

from routes.bank_accounts import (
    router as bank_accounts_router,
    BankAccountBase,
    BankAccountCreate,
    BankAccountUpdate,
    BankAccountResponse,
    BankAccountListResponse
)

__all__ = [
    # ==================== Routers ====================
    'auth_router',
    'users_router',
    'expenses_router',
    'payments_router',
    'dashboard_router',
    'bank_accounts_router',
    
    # ==================== Auth helpers ====================
    'get_current_user',
    'require_permission',
    'hash_password',
    'verify_password',
    'create_token',
    
    # ==================== Auth models ====================
    'UserLogin',
    'UserCreate',
    'UserUpdate',
    'UserResponse',
    'TokenResponse',
    
    # ==================== Expense helpers ====================
    'get_next_expense_number',
    'expenses_update_amounts',
    'expenses_check_overdue',
    
    # ==================== Expense models ====================
    'ExpenseBase',
    'ExpenseCreate',
    'ExpenseUpdate',
    'ExpenseResponse',
    'ExpenseListResponse',
    
    # ==================== Payment helpers ====================
    'payments_update_amounts',
    
    # ==================== Payment models ====================
    'PaymentBase',
    'PaymentCreate',
    'PaymentResponse',
    'PaymentListResponse',
    
    # ==================== Dashboard helpers ====================
    'dashboard_check_overdue',
    
    # ==================== Dashboard models ====================
    'TypeBreakdown',
    'DashboardSummary',
    'MonthlyChartItem',
    'AlertResponse',
    'UpcomingPayments',
    
    # ==================== Bank Account models ====================
    'BankAccountBase',
    'BankAccountCreate',
    'BankAccountUpdate',
    'BankAccountResponse',
    'BankAccountListResponse'
]
