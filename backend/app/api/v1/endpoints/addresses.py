from fastapi import APIRouter, Response, status

from app.api.deps import CurrentAuth, DbSession
from app.schemas.address import AddressCreate, AddressResponse, AddressUpdate
from app.schemas.catalog import ErrorResponse
from app.services import addresses

router = APIRouter(prefix="/addresses", tags=["addresses"])

NOT_FOUND = {404: {"model": ErrorResponse, "description": "address_not_found"}}


@router.get("", summary="List my delivery addresses (default first)")
def list_addresses(current: CurrentAuth, db: DbSession) -> list[AddressResponse]:
    return [AddressResponse.model_validate(a) for a in addresses.list_addresses(db, current.user)]


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    summary="Add a delivery address",
    description="The first address becomes the default automatically. "
    "Setting is_default=true clears the previous default.",
)
def create_address(data: AddressCreate, current: CurrentAuth, db: DbSession) -> AddressResponse:
    address = addresses.create_address(db, current.user, data)
    db.commit()
    return AddressResponse.model_validate(address)


@router.patch("/{address_id}", summary="Update one of my addresses", responses=NOT_FOUND)
def update_address(
    address_id: int, data: AddressUpdate, current: CurrentAuth, db: DbSession
) -> AddressResponse:
    address = addresses.update_address(db, current.user, address_id, data)
    db.commit()
    return AddressResponse.model_validate(address)


@router.delete(
    "/{address_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete one of my addresses",
    description="Existing orders keep their own copy of the address.",
    responses=NOT_FOUND,
)
def delete_address(address_id: int, current: CurrentAuth, db: DbSession) -> Response:
    addresses.delete_address(db, current.user, address_id)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
