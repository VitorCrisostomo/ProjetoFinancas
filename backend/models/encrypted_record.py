"""Mantém o contrato dos modelos financeiros sem colunas de conteúdo em claro."""

import copy
import math
from datetime import date, datetime, time
from uuid import uuid4

from sqlalchemy import event, inspect
from sqlalchemy.orm.attributes import flag_dirty, set_committed_value

from config import db
from services.data_encryption import DataEncryptionError, get_data_cipher


def encrypted_field(name):
    def get(instance):
        value = instance._financial_fields().get(name)
        if name == "date" and value is not None:
            return datetime.fromisoformat(value)
        return copy.deepcopy(value)

    def set_value(instance, value):
        fields = instance._financial_fields()
        if name == "date" and value is not None:
            if isinstance(value, date) and not isinstance(value, datetime):
                value = datetime.combine(value, time.min)
            if not isinstance(value, datetime):
                raise DataEncryptionError()
            value = value.isoformat()
        if name in instance._number_fields and value is not None:
            try:
                if isinstance(value, bool):
                    raise ValueError
                value = float(value)
                if not math.isfinite(value):
                    raise ValueError
            except (TypeError, ValueError, OverflowError) as error:
                raise DataEncryptionError() from error
        fields[name] = copy.deepcopy(value)
        flag_dirty(instance)

    return property(get, set_value)


class EncryptedRecord:
    encrypted_data = db.Column(db.Text, nullable=False)
    encryption_context = db.Column(db.String(36), nullable=False, unique=True)
    _number_fields = ()
    _defaults = {}

    def encryption_aad(self):
        return {
            "table": self.__tablename__,
            "record": self.encryption_context,
            **{field: getattr(self, field) for field in self._binding_fields},
        }

    def _financial_fields(self):
        cached = self.__dict__.get("_decrypted_fields")
        if cached is None:
            if self.encrypted_data is None:
                if inspect(self).persistent:
                    raise DataEncryptionError()
                cached = copy.deepcopy(self._defaults)
            else:
                cached = get_data_cipher().decrypt_fields(
                    self.encrypted_data, self.encryption_aad()
                )
                self._validate_fields(cached)
            self.__dict__["_decrypted_fields"] = cached
        return cached

    def _validate_fields(self, fields):
        if set(fields) != set(self._defaults):
            raise DataEncryptionError()
        if any(fields[name] is None for name in self._required_fields):
            raise DataEncryptionError()
        if any(
            not isinstance(fields[name], (float, int))
            or isinstance(fields[name], bool)
            or not math.isfinite(fields[name])
            for name in self._number_fields
        ):
            raise DataEncryptionError()
        if "date" in fields:
            try:
                datetime.fromisoformat(fields["date"])
            except (TypeError, ValueError) as error:
                raise DataEncryptionError() from error
        if any(
            value is not None and not isinstance(value, str)
            for name, value in fields.items()
            if name not in self._number_fields and name not in self._json_fields
        ):
            raise DataEncryptionError()

    def encrypt_for_storage(self):
        fields = self._financial_fields()
        self._validate_fields(fields)
        if not self.encryption_context:
            self.encryption_context = str(uuid4())
        self.encrypted_data = get_data_cipher().encrypt_fields(fields, self.encryption_aad())


def register_encryption_events(model):
    def encrypt(_mapper, _connection, record):
        record.encrypt_for_storage()

    def clear_cache(record, _attributes):
        record.__dict__.pop("_decrypted_fields", None)

    def bind_generated_id(_mapper, connection, record):
        # A chave gerada pelo SQLite só existe depois do INSERT. Vincula-a antes do COMMIT.
        record.encrypt_for_storage()
        connection.execute(
            model.__table__.update()
            .where(model.__table__.c.id == record.id)
            .values(encrypted_data=record.encrypted_data)
        )
        set_committed_value(record, "encrypted_data", record.encrypted_data)

    def preserve_fields_before_binding_change(record, _value, _old_value, _initiator):
        # Mudanças internas legítimas recriptografam os campos com o novo vínculo.
        if inspect(record).persistent:
            record._financial_fields()

    event.listen(model, "before_insert", encrypt)
    if getattr(model, "_bind_generated_id", False):
        event.listen(model, "after_insert", bind_generated_id)
    event.listen(model, "before_update", encrypt)
    event.listen(model, "expire", clear_cache)
    for field in (*model._binding_fields, "encryption_context"):
        event.listen(
            getattr(model, field), "set", preserve_fields_before_binding_change, active_history=True
        )
