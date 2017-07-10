from django.db import models


__all__ = [
    'AliasMatchLookup',
    'PrefixMatchLookup'
]


class VendorAliasPatternLookupBase(models.Lookup):
    def _validate_operands(self):
        assert self.lhs.alias in ('vendor_alias_pattern', 'exclusion_condition')
        assert type(self.rhs) == str


class AliasMatchLookup(VendorAliasPatternLookupBase):
    lookup_name = 'is_alias_match'

    def as_sql(self, compiler, connection):
        self._validate_operands()

        prefix, lhs_params = self.process_lhs(compiler, connection)
        val, rhs_params = self.process_rhs(compiler, connection)
        params = rhs_params + lhs_params
        return '%s LIKE %s' % (val, prefix), params


class PrefixMatchLookup(VendorAliasPatternLookupBase):
    lookup_name = 'is_prefix_match'

    def as_sql(self, compiler, connection):

        self._validate_operands()

        prefix, lhs_params = self.process_lhs(compiler, connection)
        val, rhs_params = self.process_rhs(compiler, connection)
        params = rhs_params + lhs_params

        return "{} LIKE {} || '%%'".format(val, prefix), params
