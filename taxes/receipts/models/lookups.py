from django.db import models


__all__ = ["AliasMatchLookup", "PrefixMatchLookup"]


class VendorAliasPatternLookupBase(models.Lookup):
    """
    Base alias lookup class
    """

    def _validate_operands(self):
        assert self.lhs.alias in ("vendor_alias_pattern", "exclusion_condition")
        assert isinstance(self.rhs, str)

    def as_sql(self, compiler, connection):
        raise NotImplementedError


class AliasMatchLookup(VendorAliasPatternLookupBase):
    lookup_name = "is_alias_match"

    def as_sql(self, compiler, connection):
        self._validate_operands()

        prefix, lhs_params = self.process_lhs(compiler, connection)
        val, rhs_params = self.process_rhs(compiler, connection)
        params = rhs_params + lhs_params
        return f"{val} LIKE {prefix}", params


class PrefixMatchLookup(VendorAliasPatternLookupBase):
    lookup_name = "is_prefix_match"

    def as_sql(self, compiler, connection):

        self._validate_operands()

        prefix, lhs_params = self.process_lhs(compiler, connection)
        val, rhs_params = self.process_rhs(compiler, connection)
        params = rhs_params + lhs_params

        return f"{val} LIKE {prefix} || '%%'", params
