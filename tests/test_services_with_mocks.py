"""Testabilidad por DI: se reemplazan los puertos por mocks (equivalente a Mockito)."""
from unittest.mock import Mock

import pytest

from application.catalog_service import CatalogService
from application.enrollment_service import EnrollmentService
from application.open_data_service import OpenDataService
from domain.errors import ExternalServiceUnavailable, GroupNotFound
from domain.group import GroupSnapshot


def group(id=1, max_=10, cur=0):
    return GroupSnapshot(id=id, subject="Cálculo", teacher="Ana", schedule="L 8-10",
                         maximum_capacity=max_, current_capacity=cur)


def test_enroll_delegates_to_gateway():
    reader, gateway = Mock(), Mock()
    reader.get_group.return_value = group()
    gateway.enroll.return_value = "inscrito"

    assert EnrollmentService(reader, gateway).enroll(5, 1) == "inscrito"
    gateway.enroll.assert_called_once_with(5, 1)


def test_enroll_unknown_group_never_touches_gateway():
    reader, gateway = Mock(), Mock()
    reader.get_group.return_value = None
    with pytest.raises(GroupNotFound):
        EnrollmentService(reader, gateway).enroll(5, 99)
    gateway.enroll.assert_not_called()


def test_catalog_hides_full_groups():
    reader = Mock()
    reader.list_groups.return_value = [group(1, 10, 3), group(2, 10, 10)]
    available = CatalogService(reader).available_groups()
    assert [g.id for g in available] == [1]


def test_group_status_labels():
    assert group(cur=10).status_label == "Sin cupos"
    assert group(cur=8).status_label == "Pocos cupos"
    assert group(cur=0).status_label == "Disponible"


def test_open_data_service_survives_one_api_down():
    ok, down, analytics = Mock(), Mock(), Mock()
    ok.name, down.name = "ies", "divipola"
    ok.fetch_records.return_value = [{"a": 1}]
    down.fetch_records.side_effect = ExternalServiceUnavailable("caída")
    analytics.load.return_value = 1

    report = OpenDataService([ok, down], analytics).refresh()

    assert report["ies"]["ok"] is True
    assert report["divipola"]["ok"] is False
