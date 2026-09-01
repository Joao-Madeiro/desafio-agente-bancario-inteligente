import pytest
from src.tools.interview_tools import calculate_score

def test_score_calculation_formal_no_debt():
    # Renda: 10000, Despesas: 2000 => Razão = 10000 / 2001 = 4.9975 * 30 = ~149.9
    # Formal: +300
    # Dependentes 0: +100
    # Dívidas Não: +100
    # Total esperado: ~650
    score = calculate_score(
        renda_mensal=10000.0,
        tipo_emprego="formal",
        despesas=2000.0,
        num_dependentes=0,
        tem_dividas="não",
    )
    assert 640 <= score <= 660

def test_score_calculation_unemployed_with_debt():
    # Renda: 0, Despesas: 1500 => Razão = 0
    # Desempregado: +0
    # Dependentes 3+: +30
    # Dívidas Sim: -100
    # Total bruto = -70 -> Clamp mínimo = 0
    score = calculate_score(
        renda_mensal=0.0,
        tipo_emprego="desempregado",
        despesas=1500.0,
        num_dependentes=4,
        tem_dividas="sim",
    )
    assert score == 0

def test_score_calculation_max_clamp():
    # Renda altíssima -> deve limitar no teto máximo de 1000
    score = calculate_score(
        renda_mensal=500000.0,
        tipo_emprego="formal",
        despesas=1000.0,
        num_dependentes=0,
        tem_dividas="não",
    )
    assert score == 1000
