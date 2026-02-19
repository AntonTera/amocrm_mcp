"""Pydantic input models for all 36 MCP tools (FR-22).

Validation-first: malformed input fails before any network call to amoCRM.
Constraints enforced:
- Batch operations: max 50 items per call (C-3)
- Pagination: limit max 250 (C-2)
- Complex lead: max 1 contact, max 1 company, max 40 custom fields per entity (C-4)
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator, model_validator

MAX_BATCH_SIZE = 50
MAX_PAGE_LIMIT = 250
MAX_CUSTOM_FIELDS_PER_ENTITY = 40

ENTITY_TYPES_FOR_NOTES = ("leads", "contacts", "companies", "customers")
ENTITY_TYPES_FOR_EVENTS = ("lead", "contact", "company", "customer", "task")
LINKABLE_ENTITY_TYPES = ("leads", "contacts", "companies", "customers")


# ---------------------------------------------------------------------------
# Shared base models
# ---------------------------------------------------------------------------


class PaginationMixin(BaseModel):
    """Common pagination parameters for list endpoints (FR-8)."""

    page: int = Field(default=1, ge=1, description="Page number")
    limit: int = Field(
        default=250,
        ge=1,
        le=MAX_PAGE_LIMIT,
        description="Items per page (max 250)",
    )


class CustomFieldInput(BaseModel):
    """Custom field value for create/update payloads."""

    field_id: int
    values: list[dict[str, Any]]


# ---------------------------------------------------------------------------
# Leads (5 tools)
# ---------------------------------------------------------------------------


class LeadsListInput(PaginationMixin):
    """Input for leads_list tool."""

    with_related: str | None = Field(
        default=None,
        description="Embed related entities: contacts, companies, catalog_elements (comma-separated)",
    )
    responsible_user_id: list[int] | None = Field(
        default=None, description="Filter by responsible user IDs"
    )
    status_id: list[int] | None = Field(
        default=None, description="Filter by status IDs"
    )
    pipeline_id: list[int] | None = Field(
        default=None, description="Filter by pipeline IDs"
    )
    created_at_from: int | None = Field(
        default=None, description="Filter created_at from (unix timestamp)"
    )
    created_at_to: int | None = Field(
        default=None, description="Filter created_at to (unix timestamp)"
    )
    updated_at_from: int | None = Field(
        default=None, description="Filter updated_at from (unix timestamp)"
    )
    updated_at_to: int | None = Field(
        default=None, description="Filter updated_at to (unix timestamp)"
    )
    closed_at_from: int | None = Field(
        default=None, description="Filter closed_at from (unix timestamp)"
    )
    closed_at_to: int | None = Field(
        default=None, description="Filter closed_at to (unix timestamp)"
    )
    query: str | None = Field(
        default=None, description="Search query string"
    )
    order_field: str | None = Field(
        default=None, description="Order by field (created_at, updated_at, id)"
    )
    order_direction: Literal["asc", "desc"] | None = Field(
        default=None, description="Order direction"
    )


class LeadsGetInput(BaseModel):
    """Input for leads_get tool."""

    id: int = Field(description="Lead ID")
    with_related: str | None = Field(
        default=None,
        description="Embed related entities: contacts, companies, catalog_elements (comma-separated)",
    )


class LeadsCreateInput(BaseModel):
    """Input for leads_create tool."""

    name: str | None = Field(default=None, description="Lead name")
    price: int | None = Field(default=None, description="Lead price/budget")
    status_id: int | None = Field(default=None, description="Pipeline status ID")
    pipeline_id: int | None = Field(default=None, description="Pipeline ID")
    responsible_user_id: int | None = Field(
        default=None, description="Responsible user ID"
    )
    custom_fields_values: list[CustomFieldInput] | None = Field(
        default=None, description="Custom field values"
    )

    @field_validator("custom_fields_values")
    @classmethod
    def validate_custom_fields_count(
        cls, v: list[CustomFieldInput] | None,
    ) -> list[CustomFieldInput] | None:
        if v is not None and len(v) > MAX_CUSTOM_FIELDS_PER_ENTITY:
            msg = f"Maximum {MAX_CUSTOM_FIELDS_PER_ENTITY} custom fields per entity"
            raise ValueError(msg)
        return v


class LeadsUpdateInput(BaseModel):
    """Input for leads_update tool."""

    id: int = Field(description="Lead ID to update")
    name: str | None = Field(default=None, description="Lead name")
    price: int | None = Field(default=None, description="Lead price/budget")
    status_id: int | None = Field(default=None, description="Pipeline status ID")
    pipeline_id: int | None = Field(default=None, description="Pipeline ID")
    responsible_user_id: int | None = Field(
        default=None, description="Responsible user ID"
    )
    custom_fields_values: list[CustomFieldInput] | None = Field(
        default=None, description="Custom field values"
    )

    @field_validator("custom_fields_values")
    @classmethod
    def validate_custom_fields_count(
        cls, v: list[CustomFieldInput] | None,
    ) -> list[CustomFieldInput] | None:
        if v is not None and len(v) > MAX_CUSTOM_FIELDS_PER_ENTITY:
            msg = f"Maximum {MAX_CUSTOM_FIELDS_PER_ENTITY} custom fields per entity"
            raise ValueError(msg)
        return v


class LeadsSearchInput(PaginationMixin):
    """Input for leads_search tool."""

    query: str = Field(description="Search query string")


# ---------------------------------------------------------------------------
# Contacts (4 tools)
# ---------------------------------------------------------------------------


class ContactsCreateInput(BaseModel):
    """Input for contacts_create tool."""

    name: str | None = Field(default=None, description="Contact name")
    first_name: str | None = Field(default=None, description="First name")
    last_name: str | None = Field(default=None, description="Last name")
    responsible_user_id: int | None = Field(
        default=None, description="Responsible user ID"
    )
    custom_fields_values: list[CustomFieldInput] | None = Field(
        default=None, description="Custom field values"
    )

    @field_validator("custom_fields_values")
    @classmethod
    def validate_custom_fields_count(
        cls, v: list[CustomFieldInput] | None,
    ) -> list[CustomFieldInput] | None:
        if v is not None and len(v) > MAX_CUSTOM_FIELDS_PER_ENTITY:
            msg = f"Maximum {MAX_CUSTOM_FIELDS_PER_ENTITY} custom fields per entity"
            raise ValueError(msg)
        return v


class ContactsGetInput(BaseModel):
    """Input for contacts_get tool."""

    id: int = Field(description="Contact ID")
    with_related: str | None = Field(
        default=None,
        description="Embed related entities (comma-separated)",
    )


class ContactsSearchInput(PaginationMixin):
    """Input for contacts_search tool."""

    query: str = Field(description="Search query string")


class ContactsUpdateInput(BaseModel):
    """Input for contacts_update tool."""

    id: int = Field(description="Contact ID to update")
    name: str | None = Field(default=None, description="Contact name")
    first_name: str | None = Field(default=None, description="First name")
    last_name: str | None = Field(default=None, description="Last name")
    responsible_user_id: int | None = Field(
        default=None, description="Responsible user ID"
    )
    custom_fields_values: list[CustomFieldInput] | None = Field(
        default=None, description="Custom field values"
    )

    @field_validator("custom_fields_values")
    @classmethod
    def validate_custom_fields_count(
        cls, v: list[CustomFieldInput] | None,
    ) -> list[CustomFieldInput] | None:
        if v is not None and len(v) > MAX_CUSTOM_FIELDS_PER_ENTITY:
            msg = f"Maximum {MAX_CUSTOM_FIELDS_PER_ENTITY} custom fields per entity"
            raise ValueError(msg)
        return v


# ---------------------------------------------------------------------------
# Companies (4 tools)
# ---------------------------------------------------------------------------


class CompaniesCreateInput(BaseModel):
    """Input for companies_create tool."""

    name: str | None = Field(default=None, description="Company name")
    responsible_user_id: int | None = Field(
        default=None, description="Responsible user ID"
    )
    custom_fields_values: list[CustomFieldInput] | None = Field(
        default=None, description="Custom field values"
    )

    @field_validator("custom_fields_values")
    @classmethod
    def validate_custom_fields_count(
        cls, v: list[CustomFieldInput] | None,
    ) -> list[CustomFieldInput] | None:
        if v is not None and len(v) > MAX_CUSTOM_FIELDS_PER_ENTITY:
            msg = f"Maximum {MAX_CUSTOM_FIELDS_PER_ENTITY} custom fields per entity"
            raise ValueError(msg)
        return v


class CompaniesGetInput(BaseModel):
    """Input for companies_get tool."""

    id: int = Field(description="Company ID")
    with_related: str | None = Field(
        default=None,
        description="Embed related entities (comma-separated)",
    )


class CompaniesSearchInput(PaginationMixin):
    """Input for companies_search tool."""

    query: str = Field(description="Search query string")


class CompaniesUpdateInput(BaseModel):
    """Input for companies_update tool."""

    id: int = Field(description="Company ID to update")
    name: str | None = Field(default=None, description="Company name")
    responsible_user_id: int | None = Field(
        default=None, description="Responsible user ID"
    )
    custom_fields_values: list[CustomFieldInput] | None = Field(
        default=None, description="Custom field values"
    )

    @field_validator("custom_fields_values")
    @classmethod
    def validate_custom_fields_count(
        cls, v: list[CustomFieldInput] | None,
    ) -> list[CustomFieldInput] | None:
        if v is not None and len(v) > MAX_CUSTOM_FIELDS_PER_ENTITY:
            msg = f"Maximum {MAX_CUSTOM_FIELDS_PER_ENTITY} custom fields per entity"
            raise ValueError(msg)
        return v


# ---------------------------------------------------------------------------
# Tasks (4 tools)
# ---------------------------------------------------------------------------


class TasksCreateInput(BaseModel):
    """Input for tasks_create tool."""

    text: str = Field(description="Task text/description")
    entity_id: int | None = Field(
        default=None, description="Linked entity ID"
    )
    entity_type: str | None = Field(
        default=None, description="Linked entity type (leads, contacts, companies)"
    )
    complete_till: int = Field(
        description="Task deadline as unix timestamp"
    )
    task_type_id: int | None = Field(
        default=None, description="Task type ID"
    )
    responsible_user_id: int | None = Field(
        default=None, description="Responsible user ID"
    )


class TasksGetInput(BaseModel):
    """Input for tasks_get tool."""

    id: int = Field(description="Task ID")


class TasksListInput(PaginationMixin):
    """Input for tasks_list tool."""

    entity_type: str | None = Field(
        default=None, description="Filter by entity type (leads, contacts, companies)"
    )
    entity_id: int | None = Field(
        default=None, description="Filter by linked entity ID"
    )
    responsible_user_id: list[int] | None = Field(
        default=None, description="Filter by responsible user IDs"
    )
    is_completed: bool | None = Field(
        default=None, description="Filter by completion status"
    )


class TasksUpdateInput(BaseModel):
    """Input for tasks_update tool."""

    id: int = Field(description="Task ID to update")
    text: str | None = Field(default=None, description="Task text/description")
    complete_till: int | None = Field(
        default=None, description="Task deadline as unix timestamp"
    )
    task_type_id: int | None = Field(
        default=None, description="Task type ID"
    )
    responsible_user_id: int | None = Field(
        default=None, description="Responsible user ID"
    )
    is_completed: bool | None = Field(
        default=None, description="Whether the task is completed"
    )


# ---------------------------------------------------------------------------
# Notes (2 tools)
# ---------------------------------------------------------------------------


class NotesCreateInput(BaseModel):
    """Input for notes_create tool."""

    entity_type: str = Field(
        description="Entity type: leads, contacts, companies, customers"
    )
    entity_id: int = Field(description="Entity ID to attach note to")
    note_type: str = Field(
        default="common",
        description="Note type (common, call_in, call_out, etc.)",
    )
    text: str | None = Field(default=None, description="Note text content")
    params: dict[str, Any] | None = Field(
        default=None,
        description="Additional note parameters (depends on note_type)",
    )

    @field_validator("entity_type")
    @classmethod
    def validate_entity_type(cls, v: str) -> str:
        if v not in ENTITY_TYPES_FOR_NOTES:
            msg = f"entity_type must be one of {ENTITY_TYPES_FOR_NOTES}, got '{v}'"
            raise ValueError(msg)
        return v


class NotesListInput(PaginationMixin):
    """Input for notes_list tool."""

    entity_type: str = Field(
        description="Entity type: leads, contacts, companies, customers"
    )
    entity_id: int = Field(description="Entity ID to list notes for")
    note_type: str | None = Field(
        default=None, description="Filter by note type"
    )

    @field_validator("entity_type")
    @classmethod
    def validate_entity_type(cls, v: str) -> str:
        if v not in ENTITY_TYPES_FOR_NOTES:
            msg = f"entity_type must be one of {ENTITY_TYPES_FOR_NOTES}, got '{v}'"
            raise ValueError(msg)
        return v


# ---------------------------------------------------------------------------
# Pipelines (3 tools)
# ---------------------------------------------------------------------------


class PipelinesListInput(BaseModel):
    """Input for pipelines_list tool."""


class PipelinesGetInput(BaseModel):
    """Input for pipelines_get tool."""

    pipeline_id: int = Field(description="Pipeline ID")


class PipelinesListStatusesInput(BaseModel):
    """Input for pipelines_list_statuses tool."""

    pipeline_id: int = Field(description="Pipeline ID")


# ---------------------------------------------------------------------------
# Associations (2 tools)
# ---------------------------------------------------------------------------


class AssociationsLinkEntitiesInput(BaseModel):
    """Input for associations_link_entities tool."""

    entity_type: str = Field(
        description="Source entity type (leads, contacts, companies, customers)"
    )
    entity_id: int = Field(description="Source entity ID")
    to_entity_type: str = Field(
        description="Target entity type (leads, contacts, companies, customers)"
    )
    to_entity_id: int = Field(description="Target entity ID")
    metadata: dict[str, Any] | None = Field(
        default=None, description="Link metadata (e.g., is_main for contacts)"
    )

    @field_validator("entity_type", "to_entity_type")
    @classmethod
    def validate_entity_type(cls, v: str) -> str:
        if v not in LINKABLE_ENTITY_TYPES:
            msg = f"entity_type must be one of {LINKABLE_ENTITY_TYPES}, got '{v}'"
            raise ValueError(msg)
        return v


class AssociationsGetLinkedInput(BaseModel):
    """Input for associations_get_linked tool."""

    entity_type: str = Field(
        description="Source entity type (leads, contacts, companies, customers)"
    )
    entity_id: int = Field(description="Source entity ID")

    @field_validator("entity_type")
    @classmethod
    def validate_entity_type(cls, v: str) -> str:
        if v not in LINKABLE_ENTITY_TYPES:
            msg = f"entity_type must be one of {LINKABLE_ENTITY_TYPES}, got '{v}'"
            raise ValueError(msg)
        return v


# ---------------------------------------------------------------------------
# Account (3 tools)
# ---------------------------------------------------------------------------


class AccountGetInput(BaseModel):
    """Input for account_get tool."""

    with_related: str | None = Field(
        default=None,
        description="Embed related data (amojo_id, amojo_rights, users_groups, task_types, version, entity_names, datetime_settings)",
    )


class AccountListUsersInput(PaginationMixin):
    """Input for account_list_users tool."""


class AccountListCustomFieldsInput(PaginationMixin):
    """Input for account_list_custom_fields tool."""

    entity_type: str = Field(
        description="Entity type to get custom fields for (leads, contacts, companies, customers, segments, catalogs)"
    )


# ---------------------------------------------------------------------------
# Batch (3 tools) - max 50 items per call (C-3)
# ---------------------------------------------------------------------------


class BatchCreateLeadsInput(BaseModel):
    """Input for batch_create_leads tool. Max 50 items per call (C-3)."""

    items: list[dict[str, Any]] = Field(
        description="Array of lead objects to create (max 50)",
    )

    @field_validator("items")
    @classmethod
    def validate_batch_size(cls, v: list[dict[str, Any]]) -> list[dict[str, Any]]:
        if len(v) > MAX_BATCH_SIZE:
            msg = f"Maximum {MAX_BATCH_SIZE} items per batch call, got {len(v)}"
            raise ValueError(msg)
        if len(v) == 0:
            msg = "At least 1 item required"
            raise ValueError(msg)
        return v


class BatchUpdateLeadsInput(BaseModel):
    """Input for batch_update_leads tool. Max 50 items per call (C-3)."""

    items: list[dict[str, Any]] = Field(
        description="Array of lead objects to update (max 50), each must include 'id'",
    )

    @field_validator("items")
    @classmethod
    def validate_batch_size(cls, v: list[dict[str, Any]]) -> list[dict[str, Any]]:
        if len(v) > MAX_BATCH_SIZE:
            msg = f"Maximum {MAX_BATCH_SIZE} items per batch call, got {len(v)}"
            raise ValueError(msg)
        if len(v) == 0:
            msg = "At least 1 item required"
            raise ValueError(msg)
        return v


class BatchCreateContactsInput(BaseModel):
    """Input for batch_create_contacts tool. Max 50 items per call (C-3)."""

    items: list[dict[str, Any]] = Field(
        description="Array of contact objects to create (max 50)",
    )

    @field_validator("items")
    @classmethod
    def validate_batch_size(cls, v: list[dict[str, Any]]) -> list[dict[str, Any]]:
        if len(v) > MAX_BATCH_SIZE:
            msg = f"Maximum {MAX_BATCH_SIZE} items per batch call, got {len(v)}"
            raise ValueError(msg)
        if len(v) == 0:
            msg = "At least 1 item required"
            raise ValueError(msg)
        return v


# ---------------------------------------------------------------------------
# Unsorted (3 tools)
# ---------------------------------------------------------------------------


class UnsortedListInput(PaginationMixin):
    """Input for unsorted_list tool."""

    order_by: str | None = Field(
        default=None, description="Order by field"
    )
    order_direction: Literal["asc", "desc"] | None = Field(
        default=None, description="Order direction"
    )


class UnsortedAcceptInput(BaseModel):
    """Input for unsorted_accept tool."""

    uid: str = Field(description="Unsorted lead UID")
    user_id: int | None = Field(
        default=None, description="User ID to assign the lead to"
    )
    status_id: int | None = Field(
        default=None, description="Pipeline status ID to place the lead in"
    )
    pipeline_id: int | None = Field(
        default=None, description="Pipeline ID to place the lead in"
    )


class UnsortedRejectInput(BaseModel):
    """Input for unsorted_reject tool."""

    uid: str = Field(description="Unsorted lead UID")


# ---------------------------------------------------------------------------
# Analytics / Advanced (3 tools)
# ---------------------------------------------------------------------------


class AnalyticsGetEventsInput(PaginationMixin):
    """Input for analytics_get_events tool."""

    entity_type: str | None = Field(
        default=None,
        description="Filter by entity type (lead, contact, company, customer, task)",
    )
    entity_id: int | None = Field(
        default=None, description="Filter by entity ID (requires entity_type)"
    )
    created_at_from: int | None = Field(
        default=None, description="Filter created_at from (unix timestamp)"
    )
    created_at_to: int | None = Field(
        default=None, description="Filter created_at to (unix timestamp)"
    )
    event_types: list[str] | None = Field(
        default=None, description="Filter by event types"
    )

    @field_validator("entity_type")
    @classmethod
    def validate_entity_type(cls, v: str | None) -> str | None:
        if v is not None and v not in ENTITY_TYPES_FOR_EVENTS:
            msg = f"entity_type must be one of {ENTITY_TYPES_FOR_EVENTS}, got '{v}'"
            raise ValueError(msg)
        return v

    @model_validator(mode="after")
    def validate_entity_id_requires_type(self) -> AnalyticsGetEventsInput:
        if self.entity_id is not None and self.entity_type is None:
            msg = "entity_id requires entity_type to be set"
            raise ValueError(msg)
        return self


class ComplexLeadContactInput(BaseModel):
    """Embedded contact for complex lead creation."""

    first_name: str | None = Field(default=None, description="First name")
    last_name: str | None = Field(default=None, description="Last name")
    name: str | None = Field(default=None, description="Contact name")
    responsible_user_id: int | None = Field(
        default=None, description="Responsible user ID"
    )
    custom_fields_values: list[CustomFieldInput] | None = Field(
        default=None, description="Custom field values"
    )

    @field_validator("custom_fields_values")
    @classmethod
    def validate_custom_fields_count(
        cls, v: list[CustomFieldInput] | None,
    ) -> list[CustomFieldInput] | None:
        if v is not None and len(v) > MAX_CUSTOM_FIELDS_PER_ENTITY:
            msg = f"Maximum {MAX_CUSTOM_FIELDS_PER_ENTITY} custom fields per entity"
            raise ValueError(msg)
        return v


class ComplexLeadCompanyInput(BaseModel):
    """Embedded company for complex lead creation."""

    name: str | None = Field(default=None, description="Company name")
    responsible_user_id: int | None = Field(
        default=None, description="Responsible user ID"
    )
    custom_fields_values: list[CustomFieldInput] | None = Field(
        default=None, description="Custom field values"
    )

    @field_validator("custom_fields_values")
    @classmethod
    def validate_custom_fields_count(
        cls, v: list[CustomFieldInput] | None,
    ) -> list[CustomFieldInput] | None:
        if v is not None and len(v) > MAX_CUSTOM_FIELDS_PER_ENTITY:
            msg = f"Maximum {MAX_CUSTOM_FIELDS_PER_ENTITY} custom fields per entity"
            raise ValueError(msg)
        return v


class ComplexLeadInput(BaseModel):
    """Input for leads_create_complex tool (FR-20, C-4).

    Atomic creation of lead + optional contact + optional company.
    Constraints: max 1 contact, max 1 company, max 40 custom fields per entity.
    """

    name: str | None = Field(default=None, description="Lead name")
    price: int | None = Field(default=None, description="Lead price/budget")
    status_id: int | None = Field(default=None, description="Pipeline status ID")
    pipeline_id: int | None = Field(default=None, description="Pipeline ID")
    responsible_user_id: int | None = Field(
        default=None, description="Responsible user ID"
    )
    custom_fields_values: list[CustomFieldInput] | None = Field(
        default=None, description="Custom field values for the lead"
    )
    contacts: list[ComplexLeadContactInput] | None = Field(
        default=None, description="Embedded contacts (max 1)"
    )
    company: ComplexLeadCompanyInput | None = Field(
        default=None, description="Embedded company (max 1)"
    )

    @field_validator("custom_fields_values")
    @classmethod
    def validate_custom_fields_count(
        cls, v: list[CustomFieldInput] | None,
    ) -> list[CustomFieldInput] | None:
        if v is not None and len(v) > MAX_CUSTOM_FIELDS_PER_ENTITY:
            msg = f"Maximum {MAX_CUSTOM_FIELDS_PER_ENTITY} custom fields per entity"
            raise ValueError(msg)
        return v

    @field_validator("contacts")
    @classmethod
    def validate_max_one_contact(
        cls, v: list[ComplexLeadContactInput] | None,
    ) -> list[ComplexLeadContactInput] | None:
        if v is not None and len(v) > 1:
            msg = "Complex lead creation allows maximum 1 contact"
            raise ValueError(msg)
        return v


class AnalyticsGetPipelineAnalyticsInput(BaseModel):
    """Input for analytics_get_pipeline_analytics tool (FR-21).

    Computed aggregation: fetches all leads for pipeline + date range,
    groups by status_id and responsible_user_id, returns counts.
    Latency scales with lead count (~4s per 250 leads).
    """

    pipeline_id: int = Field(description="Pipeline ID to analyze")
    created_at_from: int | None = Field(
        default=None, description="Filter leads created from (unix timestamp)"
    )
    created_at_to: int | None = Field(
        default=None, description="Filter leads created to (unix timestamp)"
    )
