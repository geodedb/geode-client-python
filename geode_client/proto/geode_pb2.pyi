from google.protobuf.internal import containers as _containers
from google.protobuf.internal import enum_type_wrapper as _enum_type_wrapper
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from collections.abc import Iterable as _Iterable, Mapping as _Mapping
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class IntKind(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    INT_KIND_UNSPECIFIED: _ClassVar[IntKind]
    INT: _ClassVar[IntKind]
    SMALLINT: _ClassVar[IntKind]
    BIGINT: _ClassVar[IntKind]

class FloatKind(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    FLOAT_KIND_UNSPECIFIED: _ClassVar[FloatKind]
    DOUBLE: _ClassVar[FloatKind]
    REAL: _ClassVar[FloatKind]

class StringKind(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    STRING_KIND_UNSPECIFIED: _ClassVar[StringKind]
    STRING: _ClassVar[StringKind]
    CHAR: _ClassVar[StringKind]
    VARCHAR: _ClassVar[StringKind]
    TEXT: _ClassVar[StringKind]

class BytesKind(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    BYTES_KIND_UNSPECIFIED: _ClassVar[BytesKind]
    BYTEA: _ClassVar[BytesKind]
    RAW: _ClassVar[BytesKind]
INT_KIND_UNSPECIFIED: IntKind
INT: IntKind
SMALLINT: IntKind
BIGINT: IntKind
FLOAT_KIND_UNSPECIFIED: FloatKind
DOUBLE: FloatKind
REAL: FloatKind
STRING_KIND_UNSPECIFIED: StringKind
STRING: StringKind
CHAR: StringKind
VARCHAR: StringKind
TEXT: StringKind
BYTES_KIND_UNSPECIFIED: BytesKind
BYTEA: BytesKind
RAW: BytesKind

class ClientPacket(_message.Message):
    __slots__ = ("quic",)
    QUIC_FIELD_NUMBER: _ClassVar[int]
    quic: QuicClientMessage
    def __init__(self, quic: _Optional[_Union[QuicClientMessage, _Mapping]] = ...) -> None: ...

class ServerPacket(_message.Message):
    __slots__ = ("quic",)
    QUIC_FIELD_NUMBER: _ClassVar[int]
    quic: QuicServerMessage
    def __init__(self, quic: _Optional[_Union[QuicServerMessage, _Mapping]] = ...) -> None: ...

class QuicClientMessage(_message.Message):
    __slots__ = ("hello", "execute", "pull", "ping", "cdc_diag", "cdc_ctrl", "begin", "commit", "rollback", "savepoint", "rollback_to", "backup", "restore", "upload_backup")
    HELLO_FIELD_NUMBER: _ClassVar[int]
    EXECUTE_FIELD_NUMBER: _ClassVar[int]
    PULL_FIELD_NUMBER: _ClassVar[int]
    PING_FIELD_NUMBER: _ClassVar[int]
    CDC_DIAG_FIELD_NUMBER: _ClassVar[int]
    CDC_CTRL_FIELD_NUMBER: _ClassVar[int]
    BEGIN_FIELD_NUMBER: _ClassVar[int]
    COMMIT_FIELD_NUMBER: _ClassVar[int]
    ROLLBACK_FIELD_NUMBER: _ClassVar[int]
    SAVEPOINT_FIELD_NUMBER: _ClassVar[int]
    ROLLBACK_TO_FIELD_NUMBER: _ClassVar[int]
    BACKUP_FIELD_NUMBER: _ClassVar[int]
    RESTORE_FIELD_NUMBER: _ClassVar[int]
    UPLOAD_BACKUP_FIELD_NUMBER: _ClassVar[int]
    hello: HelloRequest
    execute: ExecuteRequest
    pull: PullRequest
    ping: PingRequest
    cdc_diag: CdcDiagnosticsRequest
    cdc_ctrl: CdcControlRequest
    begin: BeginRequest
    commit: CommitRequest
    rollback: RollbackRequest
    savepoint: SavepointRequest
    rollback_to: RollbackToRequest
    backup: BackupRequest
    restore: RestoreRequest
    upload_backup: UploadBackupRequest
    def __init__(self, hello: _Optional[_Union[HelloRequest, _Mapping]] = ..., execute: _Optional[_Union[ExecuteRequest, _Mapping]] = ..., pull: _Optional[_Union[PullRequest, _Mapping]] = ..., ping: _Optional[_Union[PingRequest, _Mapping]] = ..., cdc_diag: _Optional[_Union[CdcDiagnosticsRequest, _Mapping]] = ..., cdc_ctrl: _Optional[_Union[CdcControlRequest, _Mapping]] = ..., begin: _Optional[_Union[BeginRequest, _Mapping]] = ..., commit: _Optional[_Union[CommitRequest, _Mapping]] = ..., rollback: _Optional[_Union[RollbackRequest, _Mapping]] = ..., savepoint: _Optional[_Union[SavepointRequest, _Mapping]] = ..., rollback_to: _Optional[_Union[RollbackToRequest, _Mapping]] = ..., backup: _Optional[_Union[BackupRequest, _Mapping]] = ..., restore: _Optional[_Union[RestoreRequest, _Mapping]] = ..., upload_backup: _Optional[_Union[UploadBackupRequest, _Mapping]] = ...) -> None: ...

class QuicServerMessage(_message.Message):
    __slots__ = ("hello", "execute", "pull", "ping", "cdc_diag", "cdc_ctrl", "begin", "commit", "rollback", "savepoint", "rollback_to", "backup", "restore", "upload_backup")
    HELLO_FIELD_NUMBER: _ClassVar[int]
    EXECUTE_FIELD_NUMBER: _ClassVar[int]
    PULL_FIELD_NUMBER: _ClassVar[int]
    PING_FIELD_NUMBER: _ClassVar[int]
    CDC_DIAG_FIELD_NUMBER: _ClassVar[int]
    CDC_CTRL_FIELD_NUMBER: _ClassVar[int]
    BEGIN_FIELD_NUMBER: _ClassVar[int]
    COMMIT_FIELD_NUMBER: _ClassVar[int]
    ROLLBACK_FIELD_NUMBER: _ClassVar[int]
    SAVEPOINT_FIELD_NUMBER: _ClassVar[int]
    ROLLBACK_TO_FIELD_NUMBER: _ClassVar[int]
    BACKUP_FIELD_NUMBER: _ClassVar[int]
    RESTORE_FIELD_NUMBER: _ClassVar[int]
    UPLOAD_BACKUP_FIELD_NUMBER: _ClassVar[int]
    hello: HelloResponse
    execute: ExecutionResponse
    pull: PullResponse
    ping: PingResponse
    cdc_diag: CdcDiagnosticsResponse
    cdc_ctrl: CdcControlResponse
    begin: BeginResponse
    commit: CommitResponse
    rollback: RollbackResponse
    savepoint: SavepointResponse
    rollback_to: RollbackToResponse
    backup: BackupResponse
    restore: RestoreResponse
    upload_backup: UploadBackupResponse
    def __init__(self, hello: _Optional[_Union[HelloResponse, _Mapping]] = ..., execute: _Optional[_Union[ExecutionResponse, _Mapping]] = ..., pull: _Optional[_Union[PullResponse, _Mapping]] = ..., ping: _Optional[_Union[PingResponse, _Mapping]] = ..., cdc_diag: _Optional[_Union[CdcDiagnosticsResponse, _Mapping]] = ..., cdc_ctrl: _Optional[_Union[CdcControlResponse, _Mapping]] = ..., begin: _Optional[_Union[BeginResponse, _Mapping]] = ..., commit: _Optional[_Union[CommitResponse, _Mapping]] = ..., rollback: _Optional[_Union[RollbackResponse, _Mapping]] = ..., savepoint: _Optional[_Union[SavepointResponse, _Mapping]] = ..., rollback_to: _Optional[_Union[RollbackToResponse, _Mapping]] = ..., backup: _Optional[_Union[BackupResponse, _Mapping]] = ..., restore: _Optional[_Union[RestoreResponse, _Mapping]] = ..., upload_backup: _Optional[_Union[UploadBackupResponse, _Mapping]] = ...) -> None: ...

class HelloRequest(_message.Message):
    __slots__ = ("username", "password", "tenant_id", "client_name", "client_version", "wanted_conformance")
    USERNAME_FIELD_NUMBER: _ClassVar[int]
    PASSWORD_FIELD_NUMBER: _ClassVar[int]
    TENANT_ID_FIELD_NUMBER: _ClassVar[int]
    CLIENT_NAME_FIELD_NUMBER: _ClassVar[int]
    CLIENT_VERSION_FIELD_NUMBER: _ClassVar[int]
    WANTED_CONFORMANCE_FIELD_NUMBER: _ClassVar[int]
    username: str
    password: str
    tenant_id: str
    client_name: str
    client_version: str
    wanted_conformance: str
    def __init__(self, username: _Optional[str] = ..., password: _Optional[str] = ..., tenant_id: _Optional[str] = ..., client_name: _Optional[str] = ..., client_version: _Optional[str] = ..., wanted_conformance: _Optional[str] = ...) -> None: ...

class HelloResponse(_message.Message):
    __slots__ = ("success", "session_id", "error_message", "capabilities")
    SUCCESS_FIELD_NUMBER: _ClassVar[int]
    SESSION_ID_FIELD_NUMBER: _ClassVar[int]
    ERROR_MESSAGE_FIELD_NUMBER: _ClassVar[int]
    CAPABILITIES_FIELD_NUMBER: _ClassVar[int]
    success: bool
    session_id: str
    error_message: str
    capabilities: _containers.RepeatedScalarFieldContainer[str]
    def __init__(self, success: bool = ..., session_id: _Optional[str] = ..., error_message: _Optional[str] = ..., capabilities: _Optional[_Iterable[str]] = ...) -> None: ...

class ExecuteRequest(_message.Message):
    __slots__ = ("session_id", "query", "params")
    SESSION_ID_FIELD_NUMBER: _ClassVar[int]
    QUERY_FIELD_NUMBER: _ClassVar[int]
    PARAMS_FIELD_NUMBER: _ClassVar[int]
    session_id: str
    query: str
    params: _containers.RepeatedCompositeFieldContainer[Param]
    def __init__(self, session_id: _Optional[str] = ..., query: _Optional[str] = ..., params: _Optional[_Iterable[_Union[Param, _Mapping]]] = ...) -> None: ...

class Param(_message.Message):
    __slots__ = ("name", "value")
    NAME_FIELD_NUMBER: _ClassVar[int]
    VALUE_FIELD_NUMBER: _ClassVar[int]
    name: str
    value: Value
    def __init__(self, name: _Optional[str] = ..., value: _Optional[_Union[Value, _Mapping]] = ...) -> None: ...

class PullRequest(_message.Message):
    __slots__ = ("request_id", "page_size", "session_id")
    REQUEST_ID_FIELD_NUMBER: _ClassVar[int]
    PAGE_SIZE_FIELD_NUMBER: _ClassVar[int]
    SESSION_ID_FIELD_NUMBER: _ClassVar[int]
    request_id: int
    page_size: int
    session_id: str
    def __init__(self, request_id: _Optional[int] = ..., page_size: _Optional[int] = ..., session_id: _Optional[str] = ...) -> None: ...

class PullResponse(_message.Message):
    __slots__ = ("response",)
    RESPONSE_FIELD_NUMBER: _ClassVar[int]
    response: ExecutionResponse
    def __init__(self, response: _Optional[_Union[ExecutionResponse, _Mapping]] = ...) -> None: ...

class Status(_message.Message):
    __slots__ = ("status_class", "status_subclass", "additional_statuses", "flagger_findings")
    STATUS_CLASS_FIELD_NUMBER: _ClassVar[int]
    STATUS_SUBCLASS_FIELD_NUMBER: _ClassVar[int]
    ADDITIONAL_STATUSES_FIELD_NUMBER: _ClassVar[int]
    FLAGGER_FINDINGS_FIELD_NUMBER: _ClassVar[int]
    status_class: str
    status_subclass: str
    additional_statuses: _containers.RepeatedScalarFieldContainer[str]
    flagger_findings: _containers.RepeatedScalarFieldContainer[str]
    def __init__(self, status_class: _Optional[str] = ..., status_subclass: _Optional[str] = ..., additional_statuses: _Optional[_Iterable[str]] = ..., flagger_findings: _Optional[_Iterable[str]] = ...) -> None: ...

class ExecutionResponse(_message.Message):
    __slots__ = ("status", "schema", "page", "error", "metrics", "explain", "profile", "heartbeat")
    STATUS_FIELD_NUMBER: _ClassVar[int]
    SCHEMA_FIELD_NUMBER: _ClassVar[int]
    PAGE_FIELD_NUMBER: _ClassVar[int]
    ERROR_FIELD_NUMBER: _ClassVar[int]
    METRICS_FIELD_NUMBER: _ClassVar[int]
    EXPLAIN_FIELD_NUMBER: _ClassVar[int]
    PROFILE_FIELD_NUMBER: _ClassVar[int]
    HEARTBEAT_FIELD_NUMBER: _ClassVar[int]
    status: Status
    schema: SchemaDefinition
    page: DataPage
    error: Error
    metrics: ExecutionMetrics
    explain: ExplainPayload
    profile: ProfilePayload
    heartbeat: Heartbeat
    def __init__(self, status: _Optional[_Union[Status, _Mapping]] = ..., schema: _Optional[_Union[SchemaDefinition, _Mapping]] = ..., page: _Optional[_Union[DataPage, _Mapping]] = ..., error: _Optional[_Union[Error, _Mapping]] = ..., metrics: _Optional[_Union[ExecutionMetrics, _Mapping]] = ..., explain: _Optional[_Union[ExplainPayload, _Mapping]] = ..., profile: _Optional[_Union[ProfilePayload, _Mapping]] = ..., heartbeat: _Optional[_Union[Heartbeat, _Mapping]] = ...) -> None: ...

class SchemaDefinition(_message.Message):
    __slots__ = ("columns",)
    COLUMNS_FIELD_NUMBER: _ClassVar[int]
    columns: _containers.RepeatedCompositeFieldContainer[ColumnDefinition]
    def __init__(self, columns: _Optional[_Iterable[_Union[ColumnDefinition, _Mapping]]] = ...) -> None: ...

class ColumnDefinition(_message.Message):
    __slots__ = ("name", "type")
    NAME_FIELD_NUMBER: _ClassVar[int]
    TYPE_FIELD_NUMBER: _ClassVar[int]
    name: str
    type: str
    def __init__(self, name: _Optional[str] = ..., type: _Optional[str] = ...) -> None: ...

class DataPage(_message.Message):
    __slots__ = ("rows", "final", "ordered", "order_keys")
    ROWS_FIELD_NUMBER: _ClassVar[int]
    FINAL_FIELD_NUMBER: _ClassVar[int]
    ORDERED_FIELD_NUMBER: _ClassVar[int]
    ORDER_KEYS_FIELD_NUMBER: _ClassVar[int]
    rows: _containers.RepeatedCompositeFieldContainer[Row]
    final: bool
    ordered: bool
    order_keys: _containers.RepeatedScalarFieldContainer[str]
    def __init__(self, rows: _Optional[_Iterable[_Union[Row, _Mapping]]] = ..., final: bool = ..., ordered: bool = ..., order_keys: _Optional[_Iterable[str]] = ...) -> None: ...

class Row(_message.Message):
    __slots__ = ("values",)
    VALUES_FIELD_NUMBER: _ClassVar[int]
    values: _containers.RepeatedCompositeFieldContainer[Value]
    def __init__(self, values: _Optional[_Iterable[_Union[Value, _Mapping]]] = ...) -> None: ...

class Value(_message.Message):
    __slots__ = ("null_val", "int_val", "double_val", "bool_val", "string_val", "decimal_val", "bytes_val", "list_val", "map_val", "node_val", "edge_val", "path_val", "ext_val")
    NULL_VAL_FIELD_NUMBER: _ClassVar[int]
    INT_VAL_FIELD_NUMBER: _ClassVar[int]
    DOUBLE_VAL_FIELD_NUMBER: _ClassVar[int]
    BOOL_VAL_FIELD_NUMBER: _ClassVar[int]
    STRING_VAL_FIELD_NUMBER: _ClassVar[int]
    DECIMAL_VAL_FIELD_NUMBER: _ClassVar[int]
    BYTES_VAL_FIELD_NUMBER: _ClassVar[int]
    LIST_VAL_FIELD_NUMBER: _ClassVar[int]
    MAP_VAL_FIELD_NUMBER: _ClassVar[int]
    NODE_VAL_FIELD_NUMBER: _ClassVar[int]
    EDGE_VAL_FIELD_NUMBER: _ClassVar[int]
    PATH_VAL_FIELD_NUMBER: _ClassVar[int]
    EXT_VAL_FIELD_NUMBER: _ClassVar[int]
    null_val: NullValue
    int_val: IntValue
    double_val: DoubleValue
    bool_val: bool
    string_val: StringValue
    decimal_val: DecimalValue
    bytes_val: BytesValue
    list_val: ListValue
    map_val: MapValue
    node_val: NodeValue
    edge_val: EdgeValue
    path_val: PathValue
    ext_val: ExtendedValue
    def __init__(self, null_val: _Optional[_Union[NullValue, _Mapping]] = ..., int_val: _Optional[_Union[IntValue, _Mapping]] = ..., double_val: _Optional[_Union[DoubleValue, _Mapping]] = ..., bool_val: bool = ..., string_val: _Optional[_Union[StringValue, _Mapping]] = ..., decimal_val: _Optional[_Union[DecimalValue, _Mapping]] = ..., bytes_val: _Optional[_Union[BytesValue, _Mapping]] = ..., list_val: _Optional[_Union[ListValue, _Mapping]] = ..., map_val: _Optional[_Union[MapValue, _Mapping]] = ..., node_val: _Optional[_Union[NodeValue, _Mapping]] = ..., edge_val: _Optional[_Union[EdgeValue, _Mapping]] = ..., path_val: _Optional[_Union[PathValue, _Mapping]] = ..., ext_val: _Optional[_Union[ExtendedValue, _Mapping]] = ...) -> None: ...

class NullValue(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class IntValue(_message.Message):
    __slots__ = ("value", "kind")
    VALUE_FIELD_NUMBER: _ClassVar[int]
    KIND_FIELD_NUMBER: _ClassVar[int]
    value: int
    kind: IntKind
    def __init__(self, value: _Optional[int] = ..., kind: _Optional[_Union[IntKind, str]] = ...) -> None: ...

class DoubleValue(_message.Message):
    __slots__ = ("value", "kind")
    VALUE_FIELD_NUMBER: _ClassVar[int]
    KIND_FIELD_NUMBER: _ClassVar[int]
    value: float
    kind: FloatKind
    def __init__(self, value: _Optional[float] = ..., kind: _Optional[_Union[FloatKind, str]] = ...) -> None: ...

class StringValue(_message.Message):
    __slots__ = ("value", "kind")
    VALUE_FIELD_NUMBER: _ClassVar[int]
    KIND_FIELD_NUMBER: _ClassVar[int]
    value: str
    kind: StringKind
    def __init__(self, value: _Optional[str] = ..., kind: _Optional[_Union[StringKind, str]] = ...) -> None: ...

class DecimalValue(_message.Message):
    __slots__ = ("coeff", "scale", "orig_scale", "orig_repr")
    COEFF_FIELD_NUMBER: _ClassVar[int]
    SCALE_FIELD_NUMBER: _ClassVar[int]
    ORIG_SCALE_FIELD_NUMBER: _ClassVar[int]
    ORIG_REPR_FIELD_NUMBER: _ClassVar[int]
    coeff: str
    scale: int
    orig_scale: int
    orig_repr: str
    def __init__(self, coeff: _Optional[str] = ..., scale: _Optional[int] = ..., orig_scale: _Optional[int] = ..., orig_repr: _Optional[str] = ...) -> None: ...

class BytesValue(_message.Message):
    __slots__ = ("value", "kind")
    VALUE_FIELD_NUMBER: _ClassVar[int]
    KIND_FIELD_NUMBER: _ClassVar[int]
    value: bytes
    kind: BytesKind
    def __init__(self, value: _Optional[bytes] = ..., kind: _Optional[_Union[BytesKind, str]] = ...) -> None: ...

class ListValue(_message.Message):
    __slots__ = ("values",)
    VALUES_FIELD_NUMBER: _ClassVar[int]
    values: _containers.RepeatedCompositeFieldContainer[Value]
    def __init__(self, values: _Optional[_Iterable[_Union[Value, _Mapping]]] = ...) -> None: ...

class MapEntry(_message.Message):
    __slots__ = ("key", "value")
    KEY_FIELD_NUMBER: _ClassVar[int]
    VALUE_FIELD_NUMBER: _ClassVar[int]
    key: str
    value: Value
    def __init__(self, key: _Optional[str] = ..., value: _Optional[_Union[Value, _Mapping]] = ...) -> None: ...

class MapValue(_message.Message):
    __slots__ = ("entries",)
    ENTRIES_FIELD_NUMBER: _ClassVar[int]
    entries: _containers.RepeatedCompositeFieldContainer[MapEntry]
    def __init__(self, entries: _Optional[_Iterable[_Union[MapEntry, _Mapping]]] = ...) -> None: ...

class NodeValue(_message.Message):
    __slots__ = ("id", "labels", "properties")
    ID_FIELD_NUMBER: _ClassVar[int]
    LABELS_FIELD_NUMBER: _ClassVar[int]
    PROPERTIES_FIELD_NUMBER: _ClassVar[int]
    id: int
    labels: _containers.RepeatedScalarFieldContainer[str]
    properties: _containers.RepeatedCompositeFieldContainer[MapEntry]
    def __init__(self, id: _Optional[int] = ..., labels: _Optional[_Iterable[str]] = ..., properties: _Optional[_Iterable[_Union[MapEntry, _Mapping]]] = ...) -> None: ...

class EdgeValue(_message.Message):
    __slots__ = ("id", "from_id", "to_id", "label", "properties")
    ID_FIELD_NUMBER: _ClassVar[int]
    FROM_ID_FIELD_NUMBER: _ClassVar[int]
    TO_ID_FIELD_NUMBER: _ClassVar[int]
    LABEL_FIELD_NUMBER: _ClassVar[int]
    PROPERTIES_FIELD_NUMBER: _ClassVar[int]
    id: int
    from_id: int
    to_id: int
    label: str
    properties: _containers.RepeatedCompositeFieldContainer[MapEntry]
    def __init__(self, id: _Optional[int] = ..., from_id: _Optional[int] = ..., to_id: _Optional[int] = ..., label: _Optional[str] = ..., properties: _Optional[_Iterable[_Union[MapEntry, _Mapping]]] = ...) -> None: ...

class PathValue(_message.Message):
    __slots__ = ("nodes", "edges")
    NODES_FIELD_NUMBER: _ClassVar[int]
    EDGES_FIELD_NUMBER: _ClassVar[int]
    nodes: _containers.RepeatedCompositeFieldContainer[NodeValue]
    edges: _containers.RepeatedCompositeFieldContainer[EdgeValue]
    def __init__(self, nodes: _Optional[_Iterable[_Union[NodeValue, _Mapping]]] = ..., edges: _Optional[_Iterable[_Union[EdgeValue, _Mapping]]] = ...) -> None: ...

class ExtendedValue(_message.Message):
    __slots__ = ("type_name", "text", "bytes", "int_val", "double_val", "bool_val")
    TYPE_NAME_FIELD_NUMBER: _ClassVar[int]
    TEXT_FIELD_NUMBER: _ClassVar[int]
    BYTES_FIELD_NUMBER: _ClassVar[int]
    INT_VAL_FIELD_NUMBER: _ClassVar[int]
    DOUBLE_VAL_FIELD_NUMBER: _ClassVar[int]
    BOOL_VAL_FIELD_NUMBER: _ClassVar[int]
    type_name: str
    text: str
    bytes: bytes
    int_val: int
    double_val: float
    bool_val: bool
    def __init__(self, type_name: _Optional[str] = ..., text: _Optional[str] = ..., bytes: _Optional[bytes] = ..., int_val: _Optional[int] = ..., double_val: _Optional[float] = ..., bool_val: bool = ...) -> None: ...

class Error(_message.Message):
    __slots__ = ("code", "message", "type", "anchor")
    CODE_FIELD_NUMBER: _ClassVar[int]
    MESSAGE_FIELD_NUMBER: _ClassVar[int]
    TYPE_FIELD_NUMBER: _ClassVar[int]
    ANCHOR_FIELD_NUMBER: _ClassVar[int]
    code: str
    message: str
    type: str
    anchor: str
    def __init__(self, code: _Optional[str] = ..., message: _Optional[str] = ..., type: _Optional[str] = ..., anchor: _Optional[str] = ...) -> None: ...

class ExecutionMetrics(_message.Message):
    __slots__ = ("parse_duration_ns", "plan_duration_ns", "execute_duration_ns", "total_duration_ns")
    PARSE_DURATION_NS_FIELD_NUMBER: _ClassVar[int]
    PLAN_DURATION_NS_FIELD_NUMBER: _ClassVar[int]
    EXECUTE_DURATION_NS_FIELD_NUMBER: _ClassVar[int]
    TOTAL_DURATION_NS_FIELD_NUMBER: _ClassVar[int]
    parse_duration_ns: int
    plan_duration_ns: int
    execute_duration_ns: int
    total_duration_ns: int
    def __init__(self, parse_duration_ns: _Optional[int] = ..., plan_duration_ns: _Optional[int] = ..., execute_duration_ns: _Optional[int] = ..., total_duration_ns: _Optional[int] = ...) -> None: ...

class ExplainOp(_message.Message):
    __slots__ = ("idx", "kind", "est_rows", "cost")
    IDX_FIELD_NUMBER: _ClassVar[int]
    KIND_FIELD_NUMBER: _ClassVar[int]
    EST_ROWS_FIELD_NUMBER: _ClassVar[int]
    COST_FIELD_NUMBER: _ClassVar[int]
    idx: int
    kind: str
    est_rows: int
    cost: int
    def __init__(self, idx: _Optional[int] = ..., kind: _Optional[str] = ..., est_rows: _Optional[int] = ..., cost: _Optional[int] = ...) -> None: ...

class ExplainTotals(_message.Message):
    __slots__ = ("est_rows", "cost")
    EST_ROWS_FIELD_NUMBER: _ClassVar[int]
    COST_FIELD_NUMBER: _ClassVar[int]
    est_rows: int
    cost: int
    def __init__(self, est_rows: _Optional[int] = ..., cost: _Optional[int] = ...) -> None: ...

class ExplainProperties(_message.Message):
    __slots__ = ("ordered", "limit", "offset", "distinct", "union_mode", "union_part_count")
    ORDERED_FIELD_NUMBER: _ClassVar[int]
    LIMIT_FIELD_NUMBER: _ClassVar[int]
    OFFSET_FIELD_NUMBER: _ClassVar[int]
    DISTINCT_FIELD_NUMBER: _ClassVar[int]
    UNION_MODE_FIELD_NUMBER: _ClassVar[int]
    UNION_PART_COUNT_FIELD_NUMBER: _ClassVar[int]
    ordered: bool
    limit: int
    offset: int
    distinct: bool
    union_mode: str
    union_part_count: int
    def __init__(self, ordered: bool = ..., limit: _Optional[int] = ..., offset: _Optional[int] = ..., distinct: bool = ..., union_mode: _Optional[str] = ..., union_part_count: _Optional[int] = ...) -> None: ...

class ExplainCalibrationEntry(_message.Message):
    __slots__ = ("idx", "est_rows", "actual_rows")
    IDX_FIELD_NUMBER: _ClassVar[int]
    EST_ROWS_FIELD_NUMBER: _ClassVar[int]
    ACTUAL_ROWS_FIELD_NUMBER: _ClassVar[int]
    idx: int
    est_rows: float
    actual_rows: float
    def __init__(self, idx: _Optional[int] = ..., est_rows: _Optional[float] = ..., actual_rows: _Optional[float] = ...) -> None: ...

class ExplainCalibration(_message.Message):
    __slots__ = ("mape", "entries")
    MAPE_FIELD_NUMBER: _ClassVar[int]
    ENTRIES_FIELD_NUMBER: _ClassVar[int]
    mape: float
    entries: _containers.RepeatedCompositeFieldContainer[ExplainCalibrationEntry]
    def __init__(self, mape: _Optional[float] = ..., entries: _Optional[_Iterable[_Union[ExplainCalibrationEntry, _Mapping]]] = ...) -> None: ...

class ExplainPayload(_message.Message):
    __slots__ = ("schema", "ops", "totals", "properties", "calibration", "profile_version")
    SCHEMA_FIELD_NUMBER: _ClassVar[int]
    OPS_FIELD_NUMBER: _ClassVar[int]
    TOTALS_FIELD_NUMBER: _ClassVar[int]
    PROPERTIES_FIELD_NUMBER: _ClassVar[int]
    CALIBRATION_FIELD_NUMBER: _ClassVar[int]
    PROFILE_VERSION_FIELD_NUMBER: _ClassVar[int]
    schema: str
    ops: _containers.RepeatedCompositeFieldContainer[ExplainOp]
    totals: ExplainTotals
    properties: ExplainProperties
    calibration: ExplainCalibration
    profile_version: int
    def __init__(self, schema: _Optional[str] = ..., ops: _Optional[_Iterable[_Union[ExplainOp, _Mapping]]] = ..., totals: _Optional[_Union[ExplainTotals, _Mapping]] = ..., properties: _Optional[_Union[ExplainProperties, _Mapping]] = ..., calibration: _Optional[_Union[ExplainCalibration, _Mapping]] = ..., profile_version: _Optional[int] = ...) -> None: ...

class ProfileOp(_message.Message):
    __slots__ = ("op", "phase", "id", "op_index", "input_rows", "rows", "time_ns", "cpu_time_ns", "bytes_out", "bytes_alloc", "estimate_bytes", "estimate_vs_actual", "percent_peak", "percent_net", "cumulative_time_ns", "freed_bytes", "net_after_op", "error_bytes", "error_abs_pct", "index_name", "selectivity_est")
    OP_FIELD_NUMBER: _ClassVar[int]
    PHASE_FIELD_NUMBER: _ClassVar[int]
    ID_FIELD_NUMBER: _ClassVar[int]
    OP_INDEX_FIELD_NUMBER: _ClassVar[int]
    INPUT_ROWS_FIELD_NUMBER: _ClassVar[int]
    ROWS_FIELD_NUMBER: _ClassVar[int]
    TIME_NS_FIELD_NUMBER: _ClassVar[int]
    CPU_TIME_NS_FIELD_NUMBER: _ClassVar[int]
    BYTES_OUT_FIELD_NUMBER: _ClassVar[int]
    BYTES_ALLOC_FIELD_NUMBER: _ClassVar[int]
    ESTIMATE_BYTES_FIELD_NUMBER: _ClassVar[int]
    ESTIMATE_VS_ACTUAL_FIELD_NUMBER: _ClassVar[int]
    PERCENT_PEAK_FIELD_NUMBER: _ClassVar[int]
    PERCENT_NET_FIELD_NUMBER: _ClassVar[int]
    CUMULATIVE_TIME_NS_FIELD_NUMBER: _ClassVar[int]
    FREED_BYTES_FIELD_NUMBER: _ClassVar[int]
    NET_AFTER_OP_FIELD_NUMBER: _ClassVar[int]
    ERROR_BYTES_FIELD_NUMBER: _ClassVar[int]
    ERROR_ABS_PCT_FIELD_NUMBER: _ClassVar[int]
    INDEX_NAME_FIELD_NUMBER: _ClassVar[int]
    SELECTIVITY_EST_FIELD_NUMBER: _ClassVar[int]
    op: str
    phase: str
    id: int
    op_index: int
    input_rows: int
    rows: int
    time_ns: int
    cpu_time_ns: int
    bytes_out: int
    bytes_alloc: int
    estimate_bytes: int
    estimate_vs_actual: int
    percent_peak: int
    percent_net: int
    cumulative_time_ns: int
    freed_bytes: int
    net_after_op: int
    error_bytes: int
    error_abs_pct: int
    index_name: str
    selectivity_est: float
    def __init__(self, op: _Optional[str] = ..., phase: _Optional[str] = ..., id: _Optional[int] = ..., op_index: _Optional[int] = ..., input_rows: _Optional[int] = ..., rows: _Optional[int] = ..., time_ns: _Optional[int] = ..., cpu_time_ns: _Optional[int] = ..., bytes_out: _Optional[int] = ..., bytes_alloc: _Optional[int] = ..., estimate_bytes: _Optional[int] = ..., estimate_vs_actual: _Optional[int] = ..., percent_peak: _Optional[int] = ..., percent_net: _Optional[int] = ..., cumulative_time_ns: _Optional[int] = ..., freed_bytes: _Optional[int] = ..., net_after_op: _Optional[int] = ..., error_bytes: _Optional[int] = ..., error_abs_pct: _Optional[int] = ..., index_name: _Optional[str] = ..., selectivity_est: _Optional[float] = ...) -> None: ...

class ProfilePeakContributor(_message.Message):
    __slots__ = ("op", "bytes_alloc")
    OP_FIELD_NUMBER: _ClassVar[int]
    BYTES_ALLOC_FIELD_NUMBER: _ClassVar[int]
    op: str
    bytes_alloc: int
    def __init__(self, op: _Optional[str] = ..., bytes_alloc: _Optional[int] = ...) -> None: ...

class ProfileTotals(_message.Message):
    __slots__ = ("time_ns", "peak_bytes")
    TIME_NS_FIELD_NUMBER: _ClassVar[int]
    PEAK_BYTES_FIELD_NUMBER: _ClassVar[int]
    time_ns: int
    peak_bytes: int
    def __init__(self, time_ns: _Optional[int] = ..., peak_bytes: _Optional[int] = ...) -> None: ...

class ProfileSpills(_message.Message):
    __slots__ = ("sort_spills", "distinct_spills", "union_spills", "spill_reason", "peak_bytes_at_spill", "first_spill_op_index")
    SORT_SPILLS_FIELD_NUMBER: _ClassVar[int]
    DISTINCT_SPILLS_FIELD_NUMBER: _ClassVar[int]
    UNION_SPILLS_FIELD_NUMBER: _ClassVar[int]
    SPILL_REASON_FIELD_NUMBER: _ClassVar[int]
    PEAK_BYTES_AT_SPILL_FIELD_NUMBER: _ClassVar[int]
    FIRST_SPILL_OP_INDEX_FIELD_NUMBER: _ClassVar[int]
    sort_spills: int
    distinct_spills: int
    union_spills: int
    spill_reason: str
    peak_bytes_at_spill: int
    first_spill_op_index: int
    def __init__(self, sort_spills: _Optional[int] = ..., distinct_spills: _Optional[int] = ..., union_spills: _Optional[int] = ..., spill_reason: _Optional[str] = ..., peak_bytes_at_spill: _Optional[int] = ..., first_spill_op_index: _Optional[int] = ...) -> None: ...

class ProfileMemory(_message.Message):
    __slots__ = ("net_bytes", "peak_bytes", "total_alloc_bytes")
    NET_BYTES_FIELD_NUMBER: _ClassVar[int]
    PEAK_BYTES_FIELD_NUMBER: _ClassVar[int]
    TOTAL_ALLOC_BYTES_FIELD_NUMBER: _ClassVar[int]
    net_bytes: int
    peak_bytes: int
    total_alloc_bytes: int
    def __init__(self, net_bytes: _Optional[int] = ..., peak_bytes: _Optional[int] = ..., total_alloc_bytes: _Optional[int] = ...) -> None: ...

class ProfilePlannerEstimates(_message.Message):
    __slots__ = ("sum_estimate_bytes", "sum_actual_bytes", "count_estimated_ops", "min_error_abs_pct", "max_error_abs_pct", "mean_error_abs_pct", "median_error_abs_pct", "stddev_error_abs_pct", "adjusted_estimate_factor")
    SUM_ESTIMATE_BYTES_FIELD_NUMBER: _ClassVar[int]
    SUM_ACTUAL_BYTES_FIELD_NUMBER: _ClassVar[int]
    COUNT_ESTIMATED_OPS_FIELD_NUMBER: _ClassVar[int]
    MIN_ERROR_ABS_PCT_FIELD_NUMBER: _ClassVar[int]
    MAX_ERROR_ABS_PCT_FIELD_NUMBER: _ClassVar[int]
    MEAN_ERROR_ABS_PCT_FIELD_NUMBER: _ClassVar[int]
    MEDIAN_ERROR_ABS_PCT_FIELD_NUMBER: _ClassVar[int]
    STDDEV_ERROR_ABS_PCT_FIELD_NUMBER: _ClassVar[int]
    ADJUSTED_ESTIMATE_FACTOR_FIELD_NUMBER: _ClassVar[int]
    sum_estimate_bytes: int
    sum_actual_bytes: int
    count_estimated_ops: int
    min_error_abs_pct: float
    max_error_abs_pct: float
    mean_error_abs_pct: float
    median_error_abs_pct: float
    stddev_error_abs_pct: float
    adjusted_estimate_factor: float
    def __init__(self, sum_estimate_bytes: _Optional[int] = ..., sum_actual_bytes: _Optional[int] = ..., count_estimated_ops: _Optional[int] = ..., min_error_abs_pct: _Optional[float] = ..., max_error_abs_pct: _Optional[float] = ..., mean_error_abs_pct: _Optional[float] = ..., median_error_abs_pct: _Optional[float] = ..., stddev_error_abs_pct: _Optional[float] = ..., adjusted_estimate_factor: _Optional[float] = ...) -> None: ...

class ProfileMemCurvePoint(_message.Message):
    __slots__ = ("op_index", "net_after_op")
    OP_INDEX_FIELD_NUMBER: _ClassVar[int]
    NET_AFTER_OP_FIELD_NUMBER: _ClassVar[int]
    op_index: int
    net_after_op: int
    def __init__(self, op_index: _Optional[int] = ..., net_after_op: _Optional[int] = ...) -> None: ...

class ProfileSetOp(_message.Message):
    __slots__ = ("type", "mode", "input_rows", "output_rows", "hash_dedup_size", "distinct_fill_pct")
    TYPE_FIELD_NUMBER: _ClassVar[int]
    MODE_FIELD_NUMBER: _ClassVar[int]
    INPUT_ROWS_FIELD_NUMBER: _ClassVar[int]
    OUTPUT_ROWS_FIELD_NUMBER: _ClassVar[int]
    HASH_DEDUP_SIZE_FIELD_NUMBER: _ClassVar[int]
    DISTINCT_FILL_PCT_FIELD_NUMBER: _ClassVar[int]
    type: str
    mode: str
    input_rows: int
    output_rows: int
    hash_dedup_size: int
    distinct_fill_pct: int
    def __init__(self, type: _Optional[str] = ..., mode: _Optional[str] = ..., input_rows: _Optional[int] = ..., output_rows: _Optional[int] = ..., hash_dedup_size: _Optional[int] = ..., distinct_fill_pct: _Optional[int] = ...) -> None: ...

class ProfilePayload(_message.Message):
    __slots__ = ("profile_version", "ops", "peak_contributors", "totals", "total_time_ns", "spills", "memory", "planner_estimates", "mem_curve", "setop", "hashagg_spills", "hashagg_spill_reason", "committed_txns", "graph_store_nodes", "graph_store_edges", "graph_store_dirty", "flagger_findings", "compact")
    PROFILE_VERSION_FIELD_NUMBER: _ClassVar[int]
    OPS_FIELD_NUMBER: _ClassVar[int]
    PEAK_CONTRIBUTORS_FIELD_NUMBER: _ClassVar[int]
    TOTALS_FIELD_NUMBER: _ClassVar[int]
    TOTAL_TIME_NS_FIELD_NUMBER: _ClassVar[int]
    SPILLS_FIELD_NUMBER: _ClassVar[int]
    MEMORY_FIELD_NUMBER: _ClassVar[int]
    PLANNER_ESTIMATES_FIELD_NUMBER: _ClassVar[int]
    MEM_CURVE_FIELD_NUMBER: _ClassVar[int]
    SETOP_FIELD_NUMBER: _ClassVar[int]
    HASHAGG_SPILLS_FIELD_NUMBER: _ClassVar[int]
    HASHAGG_SPILL_REASON_FIELD_NUMBER: _ClassVar[int]
    COMMITTED_TXNS_FIELD_NUMBER: _ClassVar[int]
    GRAPH_STORE_NODES_FIELD_NUMBER: _ClassVar[int]
    GRAPH_STORE_EDGES_FIELD_NUMBER: _ClassVar[int]
    GRAPH_STORE_DIRTY_FIELD_NUMBER: _ClassVar[int]
    FLAGGER_FINDINGS_FIELD_NUMBER: _ClassVar[int]
    COMPACT_FIELD_NUMBER: _ClassVar[int]
    profile_version: int
    ops: _containers.RepeatedCompositeFieldContainer[ProfileOp]
    peak_contributors: _containers.RepeatedCompositeFieldContainer[ProfilePeakContributor]
    totals: ProfileTotals
    total_time_ns: int
    spills: ProfileSpills
    memory: ProfileMemory
    planner_estimates: ProfilePlannerEstimates
    mem_curve: _containers.RepeatedCompositeFieldContainer[ProfileMemCurvePoint]
    setop: ProfileSetOp
    hashagg_spills: int
    hashagg_spill_reason: str
    committed_txns: int
    graph_store_nodes: int
    graph_store_edges: int
    graph_store_dirty: bool
    flagger_findings: _containers.RepeatedScalarFieldContainer[str]
    compact: bool
    def __init__(self, profile_version: _Optional[int] = ..., ops: _Optional[_Iterable[_Union[ProfileOp, _Mapping]]] = ..., peak_contributors: _Optional[_Iterable[_Union[ProfilePeakContributor, _Mapping]]] = ..., totals: _Optional[_Union[ProfileTotals, _Mapping]] = ..., total_time_ns: _Optional[int] = ..., spills: _Optional[_Union[ProfileSpills, _Mapping]] = ..., memory: _Optional[_Union[ProfileMemory, _Mapping]] = ..., planner_estimates: _Optional[_Union[ProfilePlannerEstimates, _Mapping]] = ..., mem_curve: _Optional[_Iterable[_Union[ProfileMemCurvePoint, _Mapping]]] = ..., setop: _Optional[_Union[ProfileSetOp, _Mapping]] = ..., hashagg_spills: _Optional[int] = ..., hashagg_spill_reason: _Optional[str] = ..., committed_txns: _Optional[int] = ..., graph_store_nodes: _Optional[int] = ..., graph_store_edges: _Optional[int] = ..., graph_store_dirty: bool = ..., flagger_findings: _Optional[_Iterable[str]] = ..., compact: bool = ...) -> None: ...

class Heartbeat(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class PingRequest(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class PingResponse(_message.Message):
    __slots__ = ("ok",)
    OK_FIELD_NUMBER: _ClassVar[int]
    ok: bool
    def __init__(self, ok: bool = ...) -> None: ...

class BeginRequest(_message.Message):
    __slots__ = ("read_only", "session_id")
    READ_ONLY_FIELD_NUMBER: _ClassVar[int]
    SESSION_ID_FIELD_NUMBER: _ClassVar[int]
    read_only: bool
    session_id: str
    def __init__(self, read_only: bool = ..., session_id: _Optional[str] = ...) -> None: ...

class BeginResponse(_message.Message):
    __slots__ = ("session_id", "tx_id")
    SESSION_ID_FIELD_NUMBER: _ClassVar[int]
    TX_ID_FIELD_NUMBER: _ClassVar[int]
    session_id: str
    tx_id: str
    def __init__(self, session_id: _Optional[str] = ..., tx_id: _Optional[str] = ...) -> None: ...

class CommitRequest(_message.Message):
    __slots__ = ("session_id",)
    SESSION_ID_FIELD_NUMBER: _ClassVar[int]
    session_id: str
    def __init__(self, session_id: _Optional[str] = ...) -> None: ...

class CommitResponse(_message.Message):
    __slots__ = ("success",)
    SUCCESS_FIELD_NUMBER: _ClassVar[int]
    success: bool
    def __init__(self, success: bool = ...) -> None: ...

class RollbackRequest(_message.Message):
    __slots__ = ("session_id",)
    SESSION_ID_FIELD_NUMBER: _ClassVar[int]
    session_id: str
    def __init__(self, session_id: _Optional[str] = ...) -> None: ...

class RollbackResponse(_message.Message):
    __slots__ = ("success",)
    SUCCESS_FIELD_NUMBER: _ClassVar[int]
    success: bool
    def __init__(self, success: bool = ...) -> None: ...

class SavepointRequest(_message.Message):
    __slots__ = ("name", "session_id")
    NAME_FIELD_NUMBER: _ClassVar[int]
    SESSION_ID_FIELD_NUMBER: _ClassVar[int]
    name: str
    session_id: str
    def __init__(self, name: _Optional[str] = ..., session_id: _Optional[str] = ...) -> None: ...

class SavepointResponse(_message.Message):
    __slots__ = ("success",)
    SUCCESS_FIELD_NUMBER: _ClassVar[int]
    success: bool
    def __init__(self, success: bool = ...) -> None: ...

class RollbackToRequest(_message.Message):
    __slots__ = ("name", "session_id")
    NAME_FIELD_NUMBER: _ClassVar[int]
    SESSION_ID_FIELD_NUMBER: _ClassVar[int]
    name: str
    session_id: str
    def __init__(self, name: _Optional[str] = ..., session_id: _Optional[str] = ...) -> None: ...

class RollbackToResponse(_message.Message):
    __slots__ = ("success",)
    SUCCESS_FIELD_NUMBER: _ClassVar[int]
    success: bool
    def __init__(self, success: bool = ...) -> None: ...

class CdcDiagnosticsRequest(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class CdcDiagnosticsConfig(_message.Message):
    __slots__ = ("enabled", "malformed_snapshot_interval", "malformed_hash_retain", "malformed_warn_pct", "malformed_abort_pct", "flush_interval_ms", "batch_size", "pending_backpressure_watermark")
    ENABLED_FIELD_NUMBER: _ClassVar[int]
    MALFORMED_SNAPSHOT_INTERVAL_FIELD_NUMBER: _ClassVar[int]
    MALFORMED_HASH_RETAIN_FIELD_NUMBER: _ClassVar[int]
    MALFORMED_WARN_PCT_FIELD_NUMBER: _ClassVar[int]
    MALFORMED_ABORT_PCT_FIELD_NUMBER: _ClassVar[int]
    FLUSH_INTERVAL_MS_FIELD_NUMBER: _ClassVar[int]
    BATCH_SIZE_FIELD_NUMBER: _ClassVar[int]
    PENDING_BACKPRESSURE_WATERMARK_FIELD_NUMBER: _ClassVar[int]
    enabled: bool
    malformed_snapshot_interval: int
    malformed_hash_retain: int
    malformed_warn_pct: float
    malformed_abort_pct: float
    flush_interval_ms: int
    batch_size: int
    pending_backpressure_watermark: int
    def __init__(self, enabled: bool = ..., malformed_snapshot_interval: _Optional[int] = ..., malformed_hash_retain: _Optional[int] = ..., malformed_warn_pct: _Optional[float] = ..., malformed_abort_pct: _Optional[float] = ..., flush_interval_ms: _Optional[int] = ..., batch_size: _Optional[int] = ..., pending_backpressure_watermark: _Optional[int] = ...) -> None: ...

class CdcDiagnosticsEngine(_message.Message):
    __slots__ = ("is_running", "last_flush_ms", "peak_buffer", "current_buffer", "dynamic_batch_size", "batch_adjustments")
    IS_RUNNING_FIELD_NUMBER: _ClassVar[int]
    LAST_FLUSH_MS_FIELD_NUMBER: _ClassVar[int]
    PEAK_BUFFER_FIELD_NUMBER: _ClassVar[int]
    CURRENT_BUFFER_FIELD_NUMBER: _ClassVar[int]
    DYNAMIC_BATCH_SIZE_FIELD_NUMBER: _ClassVar[int]
    BATCH_ADJUSTMENTS_FIELD_NUMBER: _ClassVar[int]
    is_running: bool
    last_flush_ms: int
    peak_buffer: int
    current_buffer: int
    dynamic_batch_size: int
    batch_adjustments: int
    def __init__(self, is_running: bool = ..., last_flush_ms: _Optional[int] = ..., peak_buffer: _Optional[int] = ..., current_buffer: _Optional[int] = ..., dynamic_batch_size: _Optional[int] = ..., batch_adjustments: _Optional[int] = ...) -> None: ...

class CdcMalformedSnapshot(_message.Message):
    __slots__ = ("count", "ts_ms")
    COUNT_FIELD_NUMBER: _ClassVar[int]
    TS_MS_FIELD_NUMBER: _ClassVar[int]
    count: int
    ts_ms: int
    def __init__(self, count: _Optional[int] = ..., ts_ms: _Optional[int] = ...) -> None: ...

class CdcMalformedHash(_message.Message):
    __slots__ = ("count", "hash", "ts_ms", "prefix_hex")
    COUNT_FIELD_NUMBER: _ClassVar[int]
    HASH_FIELD_NUMBER: _ClassVar[int]
    TS_MS_FIELD_NUMBER: _ClassVar[int]
    PREFIX_HEX_FIELD_NUMBER: _ClassVar[int]
    count: int
    hash: int
    ts_ms: int
    prefix_hex: str
    def __init__(self, count: _Optional[int] = ..., hash: _Optional[int] = ..., ts_ms: _Optional[int] = ..., prefix_hex: _Optional[str] = ...) -> None: ...

class CdcDiagnosticsResponse(_message.Message):
    __slots__ = ("malformed_change_records", "total_change_attempts", "malformed_ratio", "guardrail_warn_triggered", "guardrail_abort_triggered", "first_warn_ts_ms", "first_abort_ts_ms", "guardrail_epoch", "uptime_ms", "backpressure", "config", "engine", "malformed_snapshots", "malformed_hashes", "version", "timestamp_ms")
    MALFORMED_CHANGE_RECORDS_FIELD_NUMBER: _ClassVar[int]
    TOTAL_CHANGE_ATTEMPTS_FIELD_NUMBER: _ClassVar[int]
    MALFORMED_RATIO_FIELD_NUMBER: _ClassVar[int]
    GUARDRAIL_WARN_TRIGGERED_FIELD_NUMBER: _ClassVar[int]
    GUARDRAIL_ABORT_TRIGGERED_FIELD_NUMBER: _ClassVar[int]
    FIRST_WARN_TS_MS_FIELD_NUMBER: _ClassVar[int]
    FIRST_ABORT_TS_MS_FIELD_NUMBER: _ClassVar[int]
    GUARDRAIL_EPOCH_FIELD_NUMBER: _ClassVar[int]
    UPTIME_MS_FIELD_NUMBER: _ClassVar[int]
    BACKPRESSURE_FIELD_NUMBER: _ClassVar[int]
    CONFIG_FIELD_NUMBER: _ClassVar[int]
    ENGINE_FIELD_NUMBER: _ClassVar[int]
    MALFORMED_SNAPSHOTS_FIELD_NUMBER: _ClassVar[int]
    MALFORMED_HASHES_FIELD_NUMBER: _ClassVar[int]
    VERSION_FIELD_NUMBER: _ClassVar[int]
    TIMESTAMP_MS_FIELD_NUMBER: _ClassVar[int]
    malformed_change_records: int
    total_change_attempts: int
    malformed_ratio: float
    guardrail_warn_triggered: bool
    guardrail_abort_triggered: bool
    first_warn_ts_ms: int
    first_abort_ts_ms: int
    guardrail_epoch: int
    uptime_ms: int
    backpressure: bool
    config: CdcDiagnosticsConfig
    engine: CdcDiagnosticsEngine
    malformed_snapshots: _containers.RepeatedCompositeFieldContainer[CdcMalformedSnapshot]
    malformed_hashes: _containers.RepeatedCompositeFieldContainer[CdcMalformedHash]
    version: str
    timestamp_ms: int
    def __init__(self, malformed_change_records: _Optional[int] = ..., total_change_attempts: _Optional[int] = ..., malformed_ratio: _Optional[float] = ..., guardrail_warn_triggered: bool = ..., guardrail_abort_triggered: bool = ..., first_warn_ts_ms: _Optional[int] = ..., first_abort_ts_ms: _Optional[int] = ..., guardrail_epoch: _Optional[int] = ..., uptime_ms: _Optional[int] = ..., backpressure: bool = ..., config: _Optional[_Union[CdcDiagnosticsConfig, _Mapping]] = ..., engine: _Optional[_Union[CdcDiagnosticsEngine, _Mapping]] = ..., malformed_snapshots: _Optional[_Iterable[_Union[CdcMalformedSnapshot, _Mapping]]] = ..., malformed_hashes: _Optional[_Iterable[_Union[CdcMalformedHash, _Mapping]]] = ..., version: _Optional[str] = ..., timestamp_ms: _Optional[int] = ...) -> None: ...

class CdcControlRequest(_message.Message):
    __slots__ = ("action",)
    ACTION_FIELD_NUMBER: _ClassVar[int]
    action: str
    def __init__(self, action: _Optional[str] = ...) -> None: ...

class CdcControlResponse(_message.Message):
    __slots__ = ("success", "status", "guardrail_epoch")
    SUCCESS_FIELD_NUMBER: _ClassVar[int]
    STATUS_FIELD_NUMBER: _ClassVar[int]
    GUARDRAIL_EPOCH_FIELD_NUMBER: _ClassVar[int]
    success: bool
    status: str
    guardrail_epoch: int
    def __init__(self, success: bool = ..., status: _Optional[str] = ..., guardrail_epoch: _Optional[int] = ...) -> None: ...

class BackupRequest(_message.Message):
    __slots__ = ("backup_type", "compress")
    BACKUP_TYPE_FIELD_NUMBER: _ClassVar[int]
    COMPRESS_FIELD_NUMBER: _ClassVar[int]
    backup_type: str
    compress: bool
    def __init__(self, backup_type: _Optional[str] = ..., compress: bool = ...) -> None: ...

class BackupResponse(_message.Message):
    __slots__ = ("success", "message", "backup_id", "backup_type", "size_bytes", "compression", "checksum")
    SUCCESS_FIELD_NUMBER: _ClassVar[int]
    MESSAGE_FIELD_NUMBER: _ClassVar[int]
    BACKUP_ID_FIELD_NUMBER: _ClassVar[int]
    BACKUP_TYPE_FIELD_NUMBER: _ClassVar[int]
    SIZE_BYTES_FIELD_NUMBER: _ClassVar[int]
    COMPRESSION_FIELD_NUMBER: _ClassVar[int]
    CHECKSUM_FIELD_NUMBER: _ClassVar[int]
    success: bool
    message: str
    backup_id: str
    backup_type: str
    size_bytes: int
    compression: str
    checksum: str
    def __init__(self, success: bool = ..., message: _Optional[str] = ..., backup_id: _Optional[str] = ..., backup_type: _Optional[str] = ..., size_bytes: _Optional[int] = ..., compression: _Optional[str] = ..., checksum: _Optional[str] = ...) -> None: ...

class RestoreRequest(_message.Message):
    __slots__ = ("target_time", "confirm")
    TARGET_TIME_FIELD_NUMBER: _ClassVar[int]
    CONFIRM_FIELD_NUMBER: _ClassVar[int]
    target_time: str
    confirm: bool
    def __init__(self, target_time: _Optional[str] = ..., confirm: bool = ...) -> None: ...

class RestoreResponse(_message.Message):
    __slots__ = ("success", "message", "restore_dir", "target_time", "restore_timestamp")
    SUCCESS_FIELD_NUMBER: _ClassVar[int]
    MESSAGE_FIELD_NUMBER: _ClassVar[int]
    RESTORE_DIR_FIELD_NUMBER: _ClassVar[int]
    TARGET_TIME_FIELD_NUMBER: _ClassVar[int]
    RESTORE_TIMESTAMP_FIELD_NUMBER: _ClassVar[int]
    success: bool
    message: str
    restore_dir: str
    target_time: str
    restore_timestamp: int
    def __init__(self, success: bool = ..., message: _Optional[str] = ..., restore_dir: _Optional[str] = ..., target_time: _Optional[str] = ..., restore_timestamp: _Optional[int] = ...) -> None: ...

class UploadBackupRequest(_message.Message):
    __slots__ = ("size_bytes", "checksum")
    SIZE_BYTES_FIELD_NUMBER: _ClassVar[int]
    CHECKSUM_FIELD_NUMBER: _ClassVar[int]
    size_bytes: int
    checksum: str
    def __init__(self, size_bytes: _Optional[int] = ..., checksum: _Optional[str] = ...) -> None: ...

class UploadBackupResponse(_message.Message):
    __slots__ = ("success", "message", "upload_path")
    SUCCESS_FIELD_NUMBER: _ClassVar[int]
    MESSAGE_FIELD_NUMBER: _ClassVar[int]
    UPLOAD_PATH_FIELD_NUMBER: _ClassVar[int]
    success: bool
    message: str
    upload_path: str
    def __init__(self, success: bool = ..., message: _Optional[str] = ..., upload_path: _Optional[str] = ...) -> None: ...
