# /app/backend/models/__init__.py
# Exportación de todos los modelos

from .user import (
    UserBase, UserCreate, UserResponse, UserListResponse,
    LoginRequest, LoginResponse
)

from .expense import (
    ExpenseBase, ExpenseCreate, ExpenseUpdate, ExpenseResponse, ExpenseListResponse,
    PaymentCreate, PaymentResponse, PaymentListResponse,
    BankAccountBase, BankAccountCreate, BankAccountUpdate, BankAccountResponse, BankAccountListResponse,
    PaymentAuthorizationBase, PaymentAuthorizationCreate, PaymentAuthorizationResponse,
    PaymentAuthorizationListResponse, AuthorizationAction, ExecuteAuthorization
)

from .supplier import (
    SupplierBase, SupplierCreate, SupplierUpdate, SupplierResponse, SupplierListResponse,
    FixedExpenseBase, FixedExpenseCreate, FixedExpenseUpdate, FixedExpenseResponse, FixedExpenseListResponse
)

from .patient import (
    IGSSUnitBase, IGSSUnitCreate, IGSSUnitUpdate, IGSSUnitResponse, IGSSUnitListResponse,
    PatientBase, PatientCreate, PatientUpdate, PatientResponse, PatientListResponse, PatientSearchResponse
)

from .optica import (
    DoctorBase, DoctorCreate, DoctorUpdate, DoctorResponse, DoctorListResponse,
    FrameBase, FrameCreate, FrameUpdate, FrameResponse, FrameListResponse,
    ContactLensBase, ContactLensCreate, ContactLensUpdate, ContactLensResponse, ContactLensListResponse,
    LensTypeBase, LensTypeCreate, LensTypeUpdate, LensTypeResponse, LensTypeListResponse,
    LensItem, OpticaSaleBase, OpticaSaleCreate, OpticaSalePayment, OpticaSaleResponse, OpticaSaleListResponse,
    OpticaPurchaseBase, OpticaPurchaseCreate, OpticaPurchaseUpdate, OpticaPurchaseResponse, OpticaPurchaseListResponse
)

__all__ = [
    # User
    'UserBase', 'UserCreate', 'UserResponse', 'UserListResponse',
    'LoginRequest', 'LoginResponse',
    # Expense
    'ExpenseBase', 'ExpenseCreate', 'ExpenseUpdate', 'ExpenseResponse', 'ExpenseListResponse',
    'PaymentCreate', 'PaymentResponse', 'PaymentListResponse',
    'BankAccountBase', 'BankAccountCreate', 'BankAccountUpdate', 'BankAccountResponse', 'BankAccountListResponse',
    'PaymentAuthorizationBase', 'PaymentAuthorizationCreate', 'PaymentAuthorizationResponse',
    'PaymentAuthorizationListResponse', 'AuthorizationAction', 'ExecuteAuthorization',
    # Supplier
    'SupplierBase', 'SupplierCreate', 'SupplierUpdate', 'SupplierResponse', 'SupplierListResponse',
    'FixedExpenseBase', 'FixedExpenseCreate', 'FixedExpenseUpdate', 'FixedExpenseResponse', 'FixedExpenseListResponse',
    # Patient
    'IGSSUnitBase', 'IGSSUnitCreate', 'IGSSUnitUpdate', 'IGSSUnitResponse', 'IGSSUnitListResponse',
    'PatientBase', 'PatientCreate', 'PatientUpdate', 'PatientResponse', 'PatientListResponse', 'PatientSearchResponse',
    # Optica
    'DoctorBase', 'DoctorCreate', 'DoctorUpdate', 'DoctorResponse', 'DoctorListResponse',
    'FrameBase', 'FrameCreate', 'FrameUpdate', 'FrameResponse', 'FrameListResponse',
    'ContactLensBase', 'ContactLensCreate', 'ContactLensUpdate', 'ContactLensResponse', 'ContactLensListResponse',
    'LensTypeBase', 'LensTypeCreate', 'LensTypeUpdate', 'LensTypeResponse', 'LensTypeListResponse',
    'LensItem', 'OpticaSaleBase', 'OpticaSaleCreate', 'OpticaSalePayment', 'OpticaSaleResponse', 'OpticaSaleListResponse',
    'OpticaPurchaseBase', 'OpticaPurchaseCreate', 'OpticaPurchaseUpdate', 'OpticaPurchaseResponse', 'OpticaPurchaseListResponse',
]
