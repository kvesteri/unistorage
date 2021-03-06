from datetime import datetime

from flexmock import flexmock
import pytest

from unistorage.exceptions import FileNotFound


@pytest.mark.unit
class TestAmazonS3(object):
    def setup_method(self, method):
        pytest.importorskip("boto")

    def get_adapter_class(self):
        from unistorage.adapters.amazon import AmazonS3
        return AmazonS3

    def make_adapter(self, *args, **kwargs):
        AmazonS3 = self.get_adapter_class()
        return AmazonS3(*args, **kwargs)

    def test_constructor_creates_s3_connection_from_credentials(self):
        AmazonS3 = self.get_adapter_class()

        fake_boto = flexmock()
        (
            flexmock(AmazonS3)
            .should_receive('_import_boto')
            .and_return(fake_boto)
            .once()
        )

        fake_connection = flexmock()
        (
            fake_boto
            .should_receive('connect_s3')
            .with_args('TEST_ID', 'TEST_SECRET')
            .and_return(fake_connection)
            .once()
        )
        adapter = AmazonS3('TEST_ID', 'TEST_SECRET', 'test-bucket')
        assert adapter.connection is fake_connection

    def test_contructors_sets_bucket_name(self):
        adapter = self.make_adapter('TEST_ID', 'TEST_SECRET', 'test-bucket')
        assert adapter.bucket_name == 'test-bucket'

    def test_constructor_default_for_use_query_auth(self):
        adapter = self.make_adapter('TEST_ID', 'TEST_SECRET', 'test-bucket')
        assert adapter.use_query_auth is True

    def test_constructor_default_for_querystring_expires(self):
        adapter = self.make_adapter('TEST_ID', 'TEST_SECRET', 'test-bucket')
        assert adapter.querystring_expires == 3600

    def test_constructor_sets_use_query_auth(self):
        adapter = self.make_adapter(
            'TEST_ID', 'TEST_SECRET', 'test-bucket', use_query_auth=False
        )
        assert adapter.use_query_auth is False

    def test_constructor_sets_querystring_expires(self):
        adapter = self.make_adapter(
            'TEST_ID', 'TEST_SECRET', 'test-bucket', querystring_expires=500
        )
        assert adapter.querystring_expires == 500

    def test_get_or_create_bucket_retrieves_the_bucket_if_it_exists(self):
        adapter = self.make_adapter('TEST_ID', 'TEST_SECRET', 'test-bucket')
        fake_bucket = flexmock()
        (
            flexmock(adapter.connection)
            .should_receive('get_bucket')
            .with_args('test-bucket')
            .and_return(fake_bucket)
            .once()
        )
        bucket = adapter._get_or_create_bucket()
        assert bucket is fake_bucket

    def test_get_or_create_bucket_creates_the_bucket_unless_it_exists(self):
        from boto.exception import S3ResponseError

        adapter = self.make_adapter('TEST_ID', 'TEST_SECRET', 'test-bucket')
        (
            flexmock(adapter.connection)
            .should_receive('get_bucket')
            .with_args('test-bucket')
            .and_raise(S3ResponseError, 404, 'Not Found', '')
            .once()
        )
        fake_bucket = flexmock()
        (
            flexmock(adapter.connection)
            .should_receive('create_bucket')
            .with_args('test-bucket')
            .and_return(fake_bucket)
            .once()
        )
        bucket = adapter._get_or_create_bucket()
        assert bucket is fake_bucket

    def test_get_or_create_bucket_fails_on_permission_error(self):
        from boto.exception import S3ResponseError

        adapter = self.make_adapter('TEST_ID', 'TEST_SECRET', 'test-bucket')
        (
            flexmock(adapter.connection)
            .should_receive('get_bucket')
            .with_args('test-bucket')
            .and_raise(S3ResponseError, 403, 'Forbidden', '')
            .once()
        )
        (
            flexmock(adapter.connection)
            .should_receive('create_bucket')
            .never()
        )
        with pytest.raises(S3ResponseError):
            adapter._get_or_create_bucket()

    def test_bucket_delegates_to_get_or_create_bucket(self):
        adapter = self.make_adapter('TEST_ID', 'TEST_SECRET', 'test-bucket')
        fake_bucket = flexmock()
        (
            flexmock(adapter)
            .should_receive('_get_or_create_bucket')
            .and_return(fake_bucket)
            .once()
        )
        assert adapter.bucket is fake_bucket
        assert adapter._bucket is fake_bucket

    def test_bucket_uses_cached_bucket_if_present(self):
        adapter = self.make_adapter('TEST_ID', 'TEST_SECRET', 'test-bucket')
        adapter._bucket = flexmock()
        (
            flexmock(adapter)
            .should_receive('_get_or_create_bucket')
            .never()
        )
        assert adapter.bucket is adapter._bucket

    def test_exists_returns_false_if_file_does_not_exist(self):
        adapter = self.make_adapter('TEST_ID', 'TEST_SECRET', 'test-bucket')
        adapter._bucket = flexmock()
        fake_key = flexmock()
        (
            flexmock(adapter.bucket)
            .should_receive('new_key')
            .with_args('README.rst')
            .and_return(fake_key)
            .once()
        )
        (
            fake_key
            .should_receive('exists')
            .and_return(False)
            .once()
        )
        assert adapter.exists('README.rst') is False

    def test_exists_returns_false_if_file_does_exists(self):
        adapter = self.make_adapter('TEST_ID', 'TEST_SECRET', 'test-bucket')
        adapter._bucket = flexmock()
        fake_key = flexmock()
        (
            flexmock(adapter.bucket)
            .should_receive('new_key')
            .with_args('README.rst')
            .and_return(fake_key)
            .once()
        )
        (
            fake_key
            .should_receive('exists')
            .and_return(True)
            .once()
        )
        assert adapter.exists('README.rst') is True

    def test_delete_delegates_to_buckets_delete_key(self):
        adapter = self.make_adapter('TEST_ID', 'TEST_SECRET', 'test-bucket')
        adapter._bucket = flexmock()
        (
            flexmock(adapter.bucket)
            .should_receive('delete_key')
            .with_args('README.rst')
            .once()
        )
        adapter.delete('README.rst')

    def test_read_returns_file_contents(self):
        adapter = self.make_adapter('TEST_ID', 'TEST_SECRET', 'test-bucket')
        adapter._bucket = flexmock()
        fake_key = flexmock()
        (
            flexmock(adapter.bucket)
            .should_receive('get_key')
            .with_args('README.rst')
            .and_return(fake_key)
            .once()
        )
        (
            fake_key
            .should_receive('get_contents_as_string')
            .and_return('This is a readme.')
            .once()
        )
        content = adapter.read('README.rst')
        assert content == 'This is a readme.'

    def test_read_fails_when_reading_non_existing_file(self):
        adapter = self.make_adapter('TEST_ID', 'TEST_SECRET', 'test-bucket')
        adapter._bucket = flexmock()
        (
            flexmock(adapter.bucket)
            .should_receive('get_key')
            .with_args('README.rst')
            .and_return(None)
            .once()
        )
        with pytest.raises(FileNotFound) as exc:
            adapter.read('README.rst')
            assert exc.name == 'README.rst'

    def test_write(self):
        adapter = self.make_adapter('TEST_ID', 'TEST_SECRET', 'test-bucket')
        adapter._bucket = flexmock()
        fake_key = flexmock()
        (
            flexmock(adapter.bucket)
            .should_receive('new_key')
            .with_args('README.rst')
            .and_return(fake_key)
            .once()
        )
        (
            fake_key
            .should_receive('set_contents_from_string')
            .with_args('This is a readme.')
            .once()
        )
        adapter.write('README.rst', 'This is a readme.')

    def test_size_returns_file_size(self):
        adapter = self.make_adapter('TEST_ID', 'TEST_SECRET', 'test-bucket')
        adapter._bucket = flexmock()
        fake_key = flexmock(size=17)
        (
            flexmock(adapter.bucket)
            .should_receive('get_key')
            .with_args('README.rst')
            .and_return(fake_key)
            .once()
        )
        assert adapter.size('README.rst') == 17

    def test_size_fails_unless_file_exists(self):
        adapter = self.make_adapter('TEST_ID', 'TEST_SECRET', 'test-bucket')
        adapter._bucket = flexmock()
        (
            flexmock(adapter.bucket)
            .should_receive('get_key')
            .with_args('README.rst')
            .and_return(None)
            .once()
        )
        with pytest.raises(FileNotFound) as exc:
            adapter.size('README.rst')
            assert exc.name == 'README.rst'

    def test_modified_fails_unless_file_exists(self):
        adapter = self.make_adapter('TEST_ID', 'TEST_SECRET', 'test-bucket')
        adapter._bucket = flexmock()
        (
            flexmock(adapter.bucket)
            .should_receive('get_key')
            .with_args('README.rst')
            .and_return(None)
            .once()
        )
        with pytest.raises(FileNotFound) as exc:
            adapter.modified('README.rst')
            assert exc.name == 'README.rst'

    def test_modified_returns_last_modification_date_as_datetime(self):
        adapter = self.make_adapter('TEST_ID', 'TEST_SECRET', 'test-bucket')
        adapter._bucket = flexmock()
        fake_key = flexmock(last_modified='Sun, 14 Oct 2012 10:20:56 GMT')
        (
            flexmock(adapter.bucket)
            .should_receive('get_key')
            .with_args('README.rst')
            .and_return(fake_key)
            .once()
        )
        modified = adapter.modified('README.rst')
        assert modified == datetime(2012, 10, 14, 10, 20, 56)

    def test_modified_normalizes_timezone_to_utc(self):
        adapter = self.make_adapter('TEST_ID', 'TEST_SECRET', 'test-bucket')
        adapter._bucket = flexmock()
        fake_key = flexmock(last_modified='Sun, 14 Oct 2012 10:20:56 +0200')
        (
            flexmock(adapter.bucket)
            .should_receive('get_key')
            .with_args('README.rst')
            .and_return(fake_key)
            .once()
        )
        modified = adapter.modified('README.rst')
        assert modified == datetime(2012, 10, 14, 8, 20, 56)

    def test_url_without_querystring_authentication(self):
        adapter = self.make_adapter(
            'TEST_ID', 'TEST_SECRET', 'test-bucket', use_query_auth=False
        )
        (
            flexmock(adapter.connection)
            .should_receive('generate_url')
            .with_args(
                3600,
                'GET',
                bucket='test-bucket',
                key='README.rst',
                query_auth=False
            )
            .and_return('https://unistorage-test.s3.amazonaws.com/README.rst')
            .once()
        )
        url = adapter.url('README.rst')
        assert url == 'https://unistorage-test.s3.amazonaws.com/README.rst'

    def test_url_with_querystring_authentication(self):
        adapter = self.make_adapter(
            'TEST_ID', 'TEST_SECRET', 'test-bucket', use_query_auth=True
        )
        (
            flexmock(adapter.connection)
            .should_receive('generate_url')
            .with_args(
                3600,
                'GET',
                bucket='test-bucket',
                key='README.rst',
                query_auth=True
            )
            .and_return(
                'https://unistorage-test.s3.amazonaws.com/README.rst?'
                'Signature=U48%2FMdDwr1Kh%2BKFUtEcoqZ%2BHU7g%3D&'
                'Expires=1350217181&'
                'AWSAccessKeyId=TEST_ID'
            )
            .once()
        )
        url = adapter.url('README.rst')
        assert (
            url ==
            'https://unistorage-test.s3.amazonaws.com/README.rst?'
            'Signature=U48%2FMdDwr1Kh%2BKFUtEcoqZ%2BHU7g%3D&'
            'Expires=1350217181&'
            'AWSAccessKeyId=TEST_ID'
        )
