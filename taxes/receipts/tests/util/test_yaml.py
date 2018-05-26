"""
Yaml utility tests
"""
from io import StringIO

from taxes.receipts.util import yaml

TEST_YAML = """
data:
    primitive: mystring
    my_list: [1,2,3,4]
    my_obj:
        foo: bar
""".lstrip()


def test_load_yaml():
    expected_data = {
        'data': {
            'primitive': 'mystring',
            'my_list': [1, 2, 3, 4],
            'my_obj': {
                'foo': 'bar'
            }
        }
    }

    actual_data = yaml.load(StringIO(TEST_YAML))
    assert actual_data == expected_data
