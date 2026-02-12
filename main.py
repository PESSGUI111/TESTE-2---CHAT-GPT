import os
import sys
import hashlib
from datetime import datetime
from typing import Optional, Dict, List

import customtkinter as ctk
from PIL import Image
from peewee import (
    Model,
    SqliteDatabase,
    AutoField,
    CharField,
    BooleanField,
    DateTimeField,
    ForeignKeyField,
    FloatField,
    TextField,
    IntegerField,
)


# =========================
# APP / DB PATH
# =========================
def app_base_path() -> str:
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


DB_PATH = os.path.join(app_base_path(), "delivery.db")
db = SqliteDatabase(DB_PATH, pragmas={"foreign_keys": 1})


# =========================
# DATABASE MODELS
# =========================
class BaseModel(Model):
    class Meta:
        database = db


class Usuario(BaseModel):
    id = AutoField()
    login = CharField(unique=True)
    senha_hash = CharField()
    avatar = CharField(null=True)
    admin = BooleanField(default=False)


class Motoboy(BaseModel):
    id = AutoField()
    nome = CharField(unique=True)
    ativo = BooleanField(default=True)


class Bairro(BaseModel):
    id = AutoField()
    nome = CharField(unique=True)
    taxa_entrega = FloatField(default=0)


class Caixa(BaseModel):
    id = AutoField()
    aberto = BooleanField(default=True)
    atualizado_em = DateTimeField(default=datetime.now)


class Configuracao(BaseModel):
    id = AutoField()
    chave = CharField(unique=True)
    valor = CharField()


class Pedido(BaseModel):
    id = AutoField()
    cliente = CharField()
    canal = CharField(default="WhatsApp")
    status = CharField(default="NOVO")
    valor_produtos = FloatField(default=0)
    taxa_entrega = FloatField(default=0)
    valor_total = FloatField(default=0)
    bairro = ForeignKeyField(Bairro, null=True, backref="pedidos")
    motoboy = ForeignKeyField(Motoboy, null=True, backref="pedidos")
    forma_pagamento = CharField(default="PIX")
    pix_confirmado = BooleanField(default=False)
    observacao = TextField(null=True)
    criado_em = DateTimeField(default=datetime.now)


class LogAtividade(BaseModel):
    id = AutoField()
    usuario = ForeignKeyField(Usuario, null=True, backref="logs")
    acao = CharField()
    pedido = ForeignKeyField(Pedido, null=True, backref="logs")
    criado_em = DateTimeField(default=datetime.now)


# =========================
# CONTROLLER
# =========================
class OrderController:
    def __init__(self, usuario_logado: Usuario):
        self.usuario = usuario_logado

    def log(self, acao: str, pedido: Optional[Pedido] = None):
        LogAtividade.create(usuario=self.usuario, acao=acao, pedido=pedido)

    def fetch_orders(self) -> List[Pedido]:
        return list(Pedido.select().order_by(Pedido.id.desc()))

    def confirm_pix(self, pedido: Pedido):
        pedido.pix_confirmado = True
        if pedido.status == "PIX PENDENTE":
            pedido.status = "EM PREPARO"
        pedido.save()
        self.log("Confirmou PIX", pedido)

    def assign_motoboy(self, pedido: Pedido, motoboy: Motoboy, status: Optional[str] = None):
        if pedido.canal.upper() == "BALCÃO":
            raise ValueError("Pedido BALCÃO não pode receber motoboy.")
        pedido.motoboy = motoboy
        if status:
            pedido.status = status
        pedido.save()
        self.log(f"Atribuiu motoboy {motoboy.nome}", pedido)

    def receive_payment(self, pedido: Pedido):
        pedido.forma_pagamento = "PAGO"
        pedido.save()
        self.log("Recebeu pagamento", pedido)

    def update_observation(self, pedido: Pedido, obs: str):
        pedido.observacao = obs
        pedido.save()
        self.log("Atualizou observação", pedido)


# =========================
# THEMES / TOKENS
# =========================
THEMES: Dict[str, Dict[str, str]] = {
    "DARK": {"bg": "#1b1b1b", "panel": "#252525", "card": "#2f2f2f", "text": "#f2f2f2", "accent": "#ff9f1c"},
    "LIGHT": {"bg": "#f2f2f2", "panel": "#ffffff", "card": "#e5e5e5", "text": "#1f1f1f", "accent": "#ff9f1c"},
    "POSTIT": {"bg": "#f5f0c8", "panel": "#fff9da", "card": "#f7ef9d", "text": "#3b2f2f", "accent": "#e67e22"},
    "PINK": {"bg": "#3b0d2b", "panel": "#5e1744", "card": "#7f275e", "text": "#ffe6f2", "accent": "#ff77b4"},
    "BLUE": {"bg": "#0c1b33", "panel": "#12305f", "card": "#1d447f", "text": "#e5f0ff", "accent": "#4da3ff"},
}

ZOOM_PRESETS = {
    "GIGANTE": {"height": 160, "font": 18},
    "GRANDE": {"height": 100, "font": 15},
    "NORMAL": {"height": 75, "font": 13},
    "PEQUENO": {"height": 50, "font": 11},
}


class OrderCard(ctk.CTkFrame):
    def __init__(self, parent, order: Pedido, dashboard, height: int, font_size: int):
        super().__init__(parent, corner_radius=8, border_width=1)
        self.parent = parent
        self.order = order
        self.dashboard = dashboard
        self.height = height
        self.font_size = font_size
        self.pack_propagate(False)
        self.configure(height=self.height)

        self.top_label = ctk.CTkLabel(self, anchor="w", text="")
        self.mid_label = ctk.CTkLabel(self, anchor="w", text="")
        self.bot_label = ctk.CTkLabel(self, anchor="w", text="")
        self.alert_label = ctk.CTkLabel(self, anchor="w", text="", text_color="#ff4d4d")

        self.top_label.pack(fill="x", padx=10, pady=(6, 0))
        self.mid_label.pack(fill="x", padx=10)
        self.bot_label.pack(fill="x", padx=10)
        self.alert_label.pack(fill="x", padx=10, pady=(0, 6))

        self.bind_all_widgets("<Button-1>", self.on_click)
        self.bind_all_widgets("<Double-Button-1>", self.on_double_click)

        self.refresh_ui_content()

    def bind_all_widgets(self, event, callback):
        self.bind(event, callback)
        for w in (self.top_label, self.mid_label, self.bot_label, self.alert_label):
            w.bind(event, callback)

    def on_click(self, _event=None):
        self.dashboard.select_card(self)
        if self.dashboard.route_mode_active:
            self.dashboard.route_assign_order(self.order, self)

    def on_double_click(self, _event=None):
        self.dashboard.select_card(self)
        self.dashboard.open_action_panel(self)

    def refresh_ui_content(self):
        theme = self.dashboard.theme_tokens
        status_color = {
            "NOVO": "#7cb342",
            "EM PREPARO": "#fbc02d",
            "EM ROTA": "#29b6f6",
            "FINALIZADO": "#66bb6a",
            "CANCELADO": "#ef5350",
            "PIX PENDENTE": "#ff5252",
        }.get(self.order.status, "#cccccc")

        canal_color = {
            "IFOOD": "#ff5722",
            "WHATSAPP": "#43a047",
            "BALCÃO": "#8e24aa",
        }.get(self.order.canal.upper(), "#607d8b")

        default_bg = theme["card"]
        alert_texts = []
        bg = default_bg

        if self.order.forma_pagamento.upper() == "PIX" and not self.order.pix_confirmado:
            bg = "#420000"
            alert_texts.append("⚠️ PIX PENDENTE")

        if self.order.canal.upper() == "BALCÃO" and self.order.forma_pagamento.upper() == "A RECEBER":
            alert_texts.append("💰 PAGAR NA RETIRADA")

        if self.order.observacao:
            alert_texts.append("❗ VER OBS")

        selected = self.dashboard.selected_card is self
        border_color = "#00008B" if selected else "#555555"
        border_width = 5 if selected else 1
        fg_color = "#1e3557" if selected else bg

        self.configure(border_color=border_color, border_width=border_width, fg_color=fg_color)

        bairro = self.order.bairro.nome if self.order.bairro else "-"
        moto = self.order.motoboy.nome if self.order.motoboy else "Sem motoboy"
        elapsed = datetime.now() - self.order.criado_em
        mins = int(elapsed.total_seconds() // 60)

        self.top_label.configure(
            text=f"#{self.order.id} | {self.order.cliente} | [{self.order.canal}]",
            text_color=canal_color,
            font=("Segoe UI", self.font_size, "bold"),
        )
        self.mid_label.configure(
            text=f"{self.order.status} | R$ {self.order.valor_produtos:.2f} + R$ {self.order.taxa_entrega:.2f} = R$ {self.order.valor_total:.2f}",
            text_color=status_color,
            font=("Segoe UI", self.font_size),
        )
        self.bot_label.configure(
            text=f"{bairro} | 🛵 {moto} | {self.order.forma_pagamento} | ⏱️ {mins} min",
            text_color=theme["text"],
            font=("Segoe UI", max(10, self.font_size - 1)),
        )
        self.alert_label.configure(
            text=" • ".join(alert_texts),
            text_color="#ff6666" if alert_texts else theme["text"],
            font=("Segoe UI", max(9, self.font_size - 1), "bold"),
        )


class ActionPanelWindow(ctk.CTkToplevel):
    def __init__(self, dashboard, card: OrderCard):
        super().__init__(dashboard)
        self.dashboard = dashboard
        self.card = card
        self.order = card.order
        self.controller = dashboard.controller

        self.title(f"Pedido #{self.order.id}")
        self.geometry("430x520")
        self.protocol("WM_DELETE_WINDOW", self.close)
        self.bind("<Escape>", lambda _e: self.close())

        self.content = ctk.CTkFrame(self)
        self.content.pack(fill="both", expand=True, padx=10, pady=10)

        self.title_lbl = ctk.CTkLabel(self.content, text="", anchor="w", font=("Segoe UI", 18, "bold"))
        self.title_lbl.pack(fill="x", pady=(0, 8))

        self.info_lbl = ctk.CTkLabel(self.content, text="", justify="left", anchor="w")
        self.info_lbl.pack(fill="x", pady=(0, 12))

        self.confirm_pix_btn = ctk.CTkButton(self.content, text="CONFIRMAR PIX", fg_color="#c62828", command=self.safe(self.confirm_pix))
        self.confirm_pix_btn.pack(fill="x", pady=4)

        self.receive_btn = ctk.CTkButton(self.content, text="RECEBER PAGAMENTO", command=self.safe(self.receive_payment))
        self.receive_btn.pack(fill="x", pady=4)

        self.motoboy_menu = ctk.CTkOptionMenu(self.content, values=self.dashboard.active_motoboys_names(), command=self.safe(self.assign_motoboy))
        self.motoboy_menu.pack(fill="x", pady=4)

        self.obs_entry = ctk.CTkEntry(self.content, placeholder_text="Adicionar observação")
        self.obs_entry.pack(fill="x", pady=4)

        self.obs_btn = ctk.CTkButton(self.content, text="SALVAR OBSERVAÇÃO", command=self.safe(self.save_observation))
        self.obs_btn.pack(fill="x", pady=4)

        self.manage_lbl = ctk.CTkLabel(self.content, text="Gestão:")
        self.manage_lbl.pack(fill="x", pady=(10, 4))

        self.edit_btn = ctk.CTkButton(self.content, text="Editar Pedido", command=self.safe(lambda: self.dashboard.toast("Editar em breve")))
        self.edit_btn.pack(fill="x", pady=2)
        self.ocorr_btn = ctk.CTkButton(self.content, text="Registrar Ocorrência", command=self.safe(lambda: self.dashboard.toast("Ocorrência registrada")))
        self.ocorr_btn.pack(fill="x", pady=2)
        self.cancel_btn = ctk.CTkButton(self.content, text="Cancelar Pedido", fg_color="#7f1d1d", command=self.safe(self.cancel_order))
        self.cancel_btn.pack(fill="x", pady=2)

        self.close_btn = ctk.CTkButton(self.content, text="X Fechar", fg_color="#444", command=self.close)
        self.close_btn.pack(fill="x", pady=(12, 0))

        self.refresh()

    def safe(self, callback):
        def inner(*args, **kwargs):
            try:
                return callback(*args, **kwargs)
            except Exception as exc:
                self.dashboard.toast(f"Erro: {exc}")

        return inner

    def refresh(self):
        self.order = Pedido.get_by_id(self.order.id)
        self.card.order = self.order
        self.title_lbl.configure(text=f"Pedido #{self.order.id} • {self.order.cliente}")
        bairro = self.order.bairro.nome if self.order.bairro else "-"
        moto = self.order.motoboy.nome if self.order.motoboy else "Sem motoboy"
        self.info_lbl.configure(
            text=(
                f"Canal: {self.order.canal}\n"
                f"Status: {self.order.status}\n"
                f"Bairro: {bairro}\n"
                f"Pagamento: {self.order.forma_pagamento} | PIX confirmado: {self.order.pix_confirmado}\n"
                f"Motoboy: {moto}"
            )
        )
        if self.order.forma_pagamento.upper() == "PIX" and not self.order.pix_confirmado:
            self.confirm_pix_btn.configure(state="normal", fg_color="#c62828")
        else:
            self.confirm_pix_btn.configure(state="disabled", fg_color="#2e7d32")

        self.card.refresh_ui_content()

    def confirm_pix(self):
        self.controller.confirm_pix(self.order)
        self.refresh()

    def receive_payment(self):
        self.controller.receive_payment(self.order)
        self.refresh()

    def assign_motoboy(self, nome: str):
        if not nome:
            return
        motoboy = Motoboy.get_or_none(Motoboy.nome == nome)
        if motoboy:
            self.controller.assign_motoboy(self.order, motoboy)
            self.refresh()

    def save_observation(self):
        txt = self.obs_entry.get().strip()
        if txt:
            self.controller.update_observation(self.order, txt)
            self.obs_entry.delete(0, "end")
            self.refresh()

    def cancel_order(self):
        self.order.status = "CANCELADO"
        self.order.save()
        self.controller.log("Cancelou pedido", self.order)
        self.refresh()

    def close(self):
        self.destroy()


class Dashboard(ctk.CTk):
    def __init__(self, usuario: Usuario):
        super().__init__()
        self.usuario = usuario
        self.controller = OrderController(usuario)
        self.selected_card: Optional[OrderCard] = None
        self.cards: List[OrderCard] = []
        self.action_panel: Optional[ActionPanelWindow] = None
        self.route_mode_active = False
        self.route_motoboy: Optional[Motoboy] = None

        ctk.set_appearance_mode("Dark")
        self.current_theme = "DARK"
        self.theme_tokens = THEMES[self.current_theme]
        self.current_zoom = "NORMAL"

        self.title("BDF Delivery Cockpit")
        self.geometry("1440x900")
        self.configure(fg_color=self.theme_tokens["bg"])

        self.build_header()
        self.build_list()
        self.bind_shortcuts()
        self.populate_orders()

    def build_header(self):
        self.header = ctk.CTkFrame(self, fg_color=self.theme_tokens["panel"], corner_radius=0)
        self.header.pack(fill="x")

        self.logo_lbl = ctk.CTkLabel(self.header, text="🍔 BDF DELIVERY", font=("Segoe UI", 24, "bold"))
        self.logo_lbl.pack(side="left", padx=12, pady=8)

        self.caixa_lbl = ctk.CTkLabel(self.header, text="✅ CAIXA ABERTO", text_color="#31d158", font=("Segoe UI", 14, "bold"))
        self.caixa_lbl.pack(side="left", padx=10)

        self.route_btn = ctk.CTkButton(self.header, text="ROTA", width=80, command=self.toggle_route_mode)
        self.route_btn.pack(side="left", padx=6)

        self.top_btn = ctk.CTkButton(self.header, text="VOLTAR AO TOPO", width=130, command=self.scroll_top)
        self.top_btn.pack(side="left", padx=6)

        self.new_btn = ctk.CTkButton(self.header, text="NOVO PEDIDO (F4)", width=140, command=self.open_new_order)
        self.new_btn.pack(side="left", padx=6)

        self.quick_lbl = ctk.CTkLabel(self.header, text="Histórico | Backup | Financeiro | Admin")
        self.quick_lbl.pack(side="left", padx=12)

        self.zoom_menu = ctk.CTkOptionMenu(self.header, values=list(ZOOM_PRESETS.keys()), command=self.set_zoom)
        self.zoom_menu.set(self.current_zoom)
        self.zoom_menu.pack(side="right", padx=6)

        self.theme_menu = ctk.CTkOptionMenu(self.header, values=list(THEMES.keys()), command=self.set_theme)
        self.theme_menu.set(self.current_theme)
        self.theme_menu.pack(side="right", padx=6)

        self.user_lbl = ctk.CTkLabel(self.header, text=f"👤 {self.usuario.login}")
        self.user_lbl.pack(side="right", padx=12)

    def build_list(self):
        self.body = ctk.CTkFrame(self, fg_color=self.theme_tokens["bg"])
        self.body.pack(fill="both", expand=True)

        self.scroll = ctk.CTkScrollableFrame(self.body, fg_color=self.theme_tokens["bg"])
        self.scroll.pack(fill="both", expand=True, padx=8, pady=8)

    def bind_shortcuts(self):
        self.bind("<Up>", lambda _e: self.move_selection(-1))
        self.bind("<Down>", lambda _e: self.move_selection(1))
        self.bind("<Return>", lambda _e: self.enter_selected())
        self.bind("<F4>", lambda _e: self.open_new_order())

    def populate_orders(self):
        for card in self.cards:
            card.destroy()
        self.cards = []
        preset = ZOOM_PRESETS[self.current_zoom]
        for order in self.controller.fetch_orders():
            card = OrderCard(self.scroll, order, self, preset["height"], preset["font"])
            card.pack(fill="x", padx=6, pady=4)
            self.cards.append(card)

        if self.cards:
            self.select_card(self.cards[0])

    def refresh_single_order_card(self, card: OrderCard):
        card.order = Pedido.get_by_id(card.order.id)
        card.refresh_ui_content()
        if self.action_panel and self.action_panel.winfo_exists() and self.action_panel.card is card:
            self.action_panel.refresh()

    def select_card(self, card: OrderCard):
        self.selected_card = card
        for c in self.cards:
            c.refresh_ui_content()
        self.after(10, lambda: card.focus_set())

    def move_selection(self, step: int):
        if not self.cards:
            return
        if self.selected_card not in self.cards:
            self.select_card(self.cards[0])
            return
        i = self.cards.index(self.selected_card)
        nxt = max(0, min(len(self.cards) - 1, i + step))
        self.select_card(self.cards[nxt])
        y = nxt / max(1, len(self.cards) - 1)
        self.scroll._parent_canvas.yview_moveto(y)

    def enter_selected(self):
        if self.selected_card:
            self.open_action_panel(self.selected_card)

    def open_action_panel(self, card: OrderCard):
        if self.action_panel and self.action_panel.winfo_exists():
            self.action_panel.card = card
            self.action_panel.order = card.order
            self.action_panel.refresh()
            self.action_panel.focus()
            return
        self.action_panel = ActionPanelWindow(self, card)

    def set_theme(self, theme_name: str):
        self.current_theme = theme_name
        self.theme_tokens = THEMES[theme_name]
        self.configure(fg_color=self.theme_tokens["bg"])
        self.header.configure(fg_color=self.theme_tokens["panel"])
        self.body.configure(fg_color=self.theme_tokens["bg"])
        self.scroll.configure(fg_color=self.theme_tokens["bg"])
        for card in self.cards:
            card.refresh_ui_content()

    def set_zoom(self, zoom_name: str):
        self.current_zoom = zoom_name
        self.populate_orders()

    def scroll_top(self):
        self.scroll._parent_canvas.yview_moveto(0)

    def active_motoboys_names(self) -> List[str]:
        return [m.nome for m in Motoboy.select().where(Motoboy.ativo == True)]

    def toggle_route_mode(self):
        if self.route_mode_active:
            self.route_mode_active = False
            self.route_motoboy = None
            self.header.configure(fg_color=self.theme_tokens["panel"])
            self.route_btn.configure(text="ROTA")
            return

        names = self.active_motoboys_names()
        if not names:
            self.toast("Nenhum motoboy ativo")
            return
        selected_name = names[0]
        self.route_motoboy = Motoboy.get(Motoboy.nome == selected_name)
        self.route_mode_active = True
        self.header.configure(fg_color="#ff8c00")
        self.route_btn.configure(text="PARAR")

    def route_assign_order(self, order: Pedido, card: OrderCard):
        if not self.route_mode_active or not self.route_motoboy:
            return
        try:
            self.controller.assign_motoboy(order, self.route_motoboy, status="EM ROTA")
            self.refresh_single_order_card(card)
        except Exception as exc:
            self.toast(str(exc))

    def open_new_order(self):
        win = ctk.CTkToplevel(self)
        win.title("Novo Pedido")
        win.geometry("420x470")

        cliente = ctk.CTkEntry(win, placeholder_text="Cliente")
        cliente.pack(fill="x", padx=12, pady=6)
        canal = ctk.CTkOptionMenu(win, values=["WhatsApp", "iFood", "BALCÃO"])
        canal.set("WhatsApp")
        canal.pack(fill="x", padx=12, pady=6)
        bairro = ctk.CTkOptionMenu(win, values=[b.nome for b in Bairro.select()])
        bairro.pack(fill="x", padx=12, pady=6)
        valor_produtos = ctk.CTkEntry(win, placeholder_text="Valor produtos")
        valor_produtos.pack(fill="x", padx=12, pady=6)
        taxa = ctk.CTkEntry(win, placeholder_text="Taxa de entrega")
        taxa.pack(fill="x", padx=12, pady=6)
        forma = ctk.CTkOptionMenu(win, values=["PIX", "DINHEIRO", "A RECEBER"])
        forma.set("PIX")
        forma.pack(fill="x", padx=12, pady=6)

        info = ctk.CTkLabel(win, text="")
        info.pack(fill="x", padx=12, pady=2)

        def on_canal_change(choice):
            if choice.upper() == "BALCÃO":
                taxa.delete(0, "end")
                taxa.insert(0, "0")
                info.configure(text="BALCÃO: taxa zerada. Enter no valor confirma forma de pagamento.")
            else:
                info.configure(text="")

        canal.configure(command=on_canal_change)

        def save_order(_event=None):
            try:
                c = cliente.get().strip() or "Cliente"
                cn = canal.get()
                b = Bairro.get_or_none(Bairro.nome == bairro.get())
                vp = float(valor_produtos.get() or "0")
                tx = 0.0 if cn.upper() == "BALCÃO" else float(taxa.get() or "0")
                fp = forma.get()

                if cn.upper() == "BALCÃO" and fp == "A RECEBER":
                    self.toast("Balcão configurado: pagar na retirada")

                Pedido.create(
                    cliente=c,
                    canal=cn,
                    status="PIX PENDENTE" if fp == "PIX" else "NOVO",
                    valor_produtos=vp,
                    taxa_entrega=tx,
                    valor_total=vp + tx,
                    bairro=b,
                    forma_pagamento=fp,
                    pix_confirmado=(fp != "PIX"),
                )
                self.controller.log("Criou novo pedido")
                win.destroy()
                self.populate_orders()
            except Exception as exc:
                self.toast(f"Erro ao salvar: {exc}")

        save_btn = ctk.CTkButton(win, text="SALVAR", command=save_order)
        save_btn.pack(fill="x", padx=12, pady=12)

        win.bind("<Return>", save_order)

    def toast(self, text: str):
        top = ctk.CTkToplevel(self)
        top.geometry("360x80")
        top.title("Aviso")
        ctk.CTkLabel(top, text=text).pack(expand=True, fill="both", padx=10, pady=10)
        top.after(1500, top.destroy)


# =========================
# BOOTSTRAP
# =========================
def password_hash(raw: str) -> str:
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def seed_data():
    db.connect(reuse_if_open=True)
    db.create_tables([Usuario, Motoboy, Bairro, Caixa, Configuracao, Pedido, LogAtividade])

    admin = Usuario.get_or_none(Usuario.login == "admin")
    if not admin:
        admin = Usuario.create(login="admin", senha_hash=password_hash("admin"), admin=True)

    if Motoboy.select().count() == 0:
        for nome in ["Carlos", "Renan", "Maya"]:
            Motoboy.create(nome=nome, ativo=True)

    if Bairro.select().count() == 0:
        for nome, taxa in [("Centro", 5), ("Jardim", 8), ("Industrial", 10)]:
            Bairro.create(nome=nome, taxa_entrega=taxa)

    if Caixa.select().count() == 0:
        Caixa.create(aberto=True)

    if Pedido.select().count() == 0:
        centro = Bairro.get(Bairro.nome == "Centro")
        Pedido.create(
            cliente="Ana Souza",
            canal="WhatsApp",
            status="PIX PENDENTE",
            valor_produtos=42.0,
            taxa_entrega=5.0,
            valor_total=47.0,
            bairro=centro,
            forma_pagamento="PIX",
            pix_confirmado=False,
            observacao="Sem cebola",
        )
        Pedido.create(
            cliente="Marcos Lima",
            canal="BALCÃO",
            status="NOVO",
            valor_produtos=25,
            taxa_entrega=0,
            valor_total=25,
            bairro=centro,
            forma_pagamento="A RECEBER",
            pix_confirmado=True,
        )

    return admin


def main():
    user = seed_data()
    app = Dashboard(user)
    app.mainloop()


if __name__ == "__main__":
    main()
