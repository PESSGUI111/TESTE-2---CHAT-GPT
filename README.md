# BDF Delivery Cockpit

Sistema desktop de gestão de pedidos e entregas para delivery com foco em fluidez e atualização cirúrgica de cards.

## Como rodar

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python main.py
```

## Entregas implementadas

- Cockpit com lista de pedidos ocupando o centro da tela.
- Navegação por teclado (`↑`, `↓`, `Enter`, `F4`).
- Card de pedido em 3 linhas, com alertas visuais críticos.
- Painel de ações persistente (fecha só no `X` ou `ESC`).
- Modo Rota para despacho rápido e bloqueio para canal BALCÃO.
- 5 temas (Dark, Light, PostIt, Pink e Blue).
- 4 zooms de densidade (Gigante, Grande, Normal, Pequeno).
- Banco SQLite com Peewee e logs de atividades.
- Cadastro rápido de pedido com regra de BALCÃO.

## Observações

- O modo rota seleciona automaticamente o primeiro motoboy ativo para acelerar despacho.
- A atualização de pedido ocorre no card afetado via `refresh_single_order_card` / `refresh_ui_content`.
