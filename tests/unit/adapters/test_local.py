import os

import pytest
from flexmock import flexmock

from unistorage.exceptions import SuspiciousFilename


def get_adapter_class():
    from unistorage.adapters.local import Local
    return Local


def make_adapter(*args, **kwargs):
    Local = get_adapter_class()
    return Local(*args, **kwargs)


class TestLocal(object):

    def test_constructor_normalizes_and_sets_directory(self):
        Local = get_adapter_class()
        (flexmock(Local)
            .should_receive('normalize_path')
            .with_args('/some/path')
            .and_return('/some/path')
            .once()
        )
        adapter = Local('/some/path')
        assert adapter.directory == '/some/path'

    def test_normalize_path_delegates_to_abspath(self):
        Local = get_adapter_class()
        (flexmock(os.path)
            .should_receive('abspath')
            .with_args('/foo/../bar')
            .and_return('/foo/bar')
            .once()
        )
        assert Local.normalize_path('/foo/../bar') == '/foo/bar'

    def test_compute_path_joins_given_name_with_base_directory(self):
        adapter = make_adapter('/some/path')
        assert adapter.compute_path('foo') == '/some/path/foo'

    def test_compute_path_fails_if_resulting_path_is_outside_base_directory(self):
        adapter = make_adapter('/some/path')
        with pytest.raises(SuspiciousFilename) as exc:
            adapter.compute_path('../foo')
            assert exc.name == '../foo'


TestLocal = pytest.mark.unit(TestLocal)
