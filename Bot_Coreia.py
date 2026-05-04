import discord
from discord.ext import commands, tasks
from discord.ui import Button, View, Modal, TextInput, UserSelect, Select
import asyncio
from datetime import datetime
import json
import os
import sys
import aiohttp
import re
import glob

# ========= CONFIGURAÇÕES =========
TOKEN = os.getenv("DISCORD_TOKEN")
if not TOKEN:
    print("ERRO: Token do Discord não encontrado!")
    sys.exit(1)

# CARGOS ADMIN / HIERARQUIA
CARGO_GERENTE_GERAL_ID = 1474106459955400769
CARGO_00_ID = 1474106459955400772
CARGO_01_ID = 1474106459955400771
CARGO_02_ID = 1474106459955400770
CARGO_ELITE_ID = 1474106459540422734
CARGO_MEMBRO_ID = 1474106459540422733
CARGO_GERENTE_FARM_ID = 1474106459955400765
CARGO_GERENTE_VENDAS_ID = 1474106459955400764

# CARGOS ADMIN (gerentes gerais + cargos 00/01/02)
CARGOS_ADMIN_IDS = [
    CARGO_GERENTE_GERAL_ID,
    CARGO_00_ID,
    CARGO_01_ID,
    CARGO_02_ID,
]

# CARGOS QUE PODEM REGISTRAR FARM (apenas membro)
CARGO_FARM_REGISTRAR_IDS = [CARGO_MEMBRO_ID]

# CARGOS QUE PODEM PUXAR AÇÃO
CARGO_REGISTRAR_ACAO_IDS = [
    CARGO_ELITE_ID,
    CARGO_00_ID,
    CARGO_01_ID,
    CARGO_02_ID,
]

# CARGOS QUE PODEM VENDER ARMA
CARGO_VENDA_ARMA_IDS = [
    CARGO_00_ID,
    CARGO_01_ID,
    CARGO_02_ID,
    CARGO_GERENTE_VENDAS_ID,
]

# CARGOS QUE PODEM COMPRAR PRODUTO
CARGO_COMPRA_PRODUTO_IDS = [
    CARGO_GERENTE_GERAL_ID,
    CARGO_00_ID,
    CARGO_01_ID,
    CARGO_02_ID,
]

# CARGOS QUE PODEM RESETAR RANK
CARGO_RESET_RANK_IDS = [
    CARGO_00_ID,
    CARGO_01_ID,
    CARGO_02_ID,
]

# CARGOS DO PAINEL DE SET (para atribuir)
CARGOS_SET = [
    {"id": CARGO_GERENTE_FARM_ID,    "nome": "Gerente de Farm"},
    {"id": CARGO_GERENTE_VENDAS_ID,  "nome": "Gerente de Vendas"},
    {"id": CARGO_ELITE_ID,           "nome": "Elite"},
    {"id": CARGO_MEMBRO_ID,          "nome": "Membro"},
    {"id": CARGO_GERENTE_GERAL_ID,   "nome": "Gerente Geral"},
]

# ========= IDs DE CANAIS / CATEGORIAS =========
CATEGORIA_FARMS_ID               = 1500689556960444558  # Categoria para canais de farm privados
CATEGORIA_PAINEL_ID              = int(os.getenv("CATEGORIA_PAINEL_ID",             "1500656745800794205"))
CATEGORIA_BACKUP_ID              = int(os.getenv("CATEGORIA_BACKUP_ID",             "1500652423465930823"))
CATEGORIA_COMPRA_VENDA_LOGS_ID   = int(os.getenv("CATEGORIA_COMPRA_VENDA_LOGS_ID",  "1500647963117228242"))
CATEGORIA_LOGS_ID                = int(os.getenv("CATEGORIA_LOGS_ID",               "1500656957059764385"))

CHAT_LOGS_ID                     = int(os.getenv("CHAT_LOGS_ID",                    "1500704028735176784"))
CHAT_ADMIN_LOGS_ID               = int(os.getenv("CHAT_ADMIN_LOGS_ID",              "1500656957059764385"))
CHAT_RANK_ID                     = int(os.getenv("CHAT_RANK_ID",                    "1500704618206859304"))
CHAT_COMPRA_VENDA_ID             = int(os.getenv("CHAT_COMPRA_VENDA_ID",            "1500704392528138270"))
LOG_REGISTROS_ID                 = int(os.getenv("LOG_REGISTROS_ID",                "1500649180153122957"))
CANAL_LIVES_PAINEL_ID            = int(os.getenv("CANAL_LIVES_PAINEL_ID",           "1498692536800252084"))
CANAL_ACOES_PAINEL_ID            = int(os.getenv("CANAL_ACOES_PAINEL_ID",           "1500647352497737748"))
CANAL_ACOES_LOGS_ID              = int(os.getenv("CANAL_ACOES_LOGS_ID",             "1500647398093881474"))
CANAL_BACKUP_ARQUIVOS_ID         = int(os.getenv("CANAL_BACKUP_ARQUIVOS_ID",        "1500652423465930823"))

# Canal do painel de SET (criar automático)
CANAL_SET_PAINEL_ID              = int(os.getenv("CANAL_SET_PAINEL_ID",             "0"))
# Canal de confirmações do SET (onde aparece o formulário para admins aprovar)
CANAL_SET_CONFIRMACAO_ID         = 1500693330739204277

TWITCH_CLIENT_ID     = os.getenv("TWITCH_CLIENT_ID")
TWITCH_CLIENT_SECRET = os.getenv("TWITCH_CLIENT_SECRET")
YOUTUBE_API_KEY      = os.getenv("YOUTUBE_API_KEY")

# Categoria para logs de admin: 1500651624597819442
CATEGORIA_ADMIN_LOGS            = 1500651624597819442

# ========= BANCO DE DADOS =========
dados = {
    "usuarios": {},
    "canais": {},
    "admins": [],
    "config": {},
    "caixa_semana": {},
    "compras_vendas": [],
    "usuarios_banidos": [],
    "dinheiro_sujo": {},
    "lives": {
        "config": {},
        "streamers": {},
        "last_notified": {},
        "status": {}
    },
    "acoes": {},
    "solicitacoes_set": {}
}

def salvar_dados():
    with open("dados_bot.json", "w", encoding="utf-8") as f:
        json.dump(dados, f, ensure_ascii=False, indent=2)

def carregar_dados():
    try:
        with open("dados_bot.json", "r", encoding="utf-8") as f:
            loaded = json.load(f)
            dados.update(loaded)
        return True
    except:
        return False

async def salvar_backup_completo(admin_name="Sistema"):
    backup_nome = f"backup_completo_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    backup = {
        "data_backup": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "admin": admin_name,
        "dados": json.loads(json.dumps(dados))
    }
    with open(backup_nome, "w", encoding="utf-8") as f:
        json.dump(backup, f, ensure_ascii=False, indent=2)
    salvar_dados()
    canal_backup = bot.get_channel(CANAL_BACKUP_ARQUIVOS_ID)
    if canal_backup and isinstance(canal_backup, discord.TextChannel):
        embed = discord.Embed(
            title="💾 BACKUP COMPLETO SALVO",
            description=f"**Arquivo:** {backup_nome}\n**Data:** {backup['data_backup']}\n**Admin:** {admin_name}",
            color=discord.Color.green()
        )
        await canal_backup.send(embed=embed)
        await canal_backup.send(file=discord.File(backup_nome))
        if os.path.exists("dados_bot.json"):
            await canal_backup.send(file=discord.File("dados_bot.json"))
    return backup_nome

async def criar_canal_compra_venda_log(tipo, dados_log):
    categoria = bot.get_channel(CATEGORIA_COMPRA_VENDA_LOGS_ID)
    if not categoria:
        return None
    data = datetime.now().strftime("%d-%m-%Y_%H-%M-%S")
    canal = await categoria.create_text_channel(f"log-{tipo}-{data}")
    embed = discord.Embed(title=f"LOG DE {tipo.upper()}", color=discord.Color.blue(), timestamp=datetime.now())
    for chave, valor in dados_log.items():
        embed.add_field(name=chave, value=valor, inline=False)
    await canal.send(embed=embed)
    return canal

async def limpar_logs_usuario(user_id, user_name):
    if str(user_id) in dados["usuarios_banidos"]:
        return 0
    dados["usuarios_banidos"].append(str(user_id))
    total_limpo = 0
    for canal_id in [CHAT_LOGS_ID, CHAT_ADMIN_LOGS_ID, CHAT_RANK_ID, CHAT_COMPRA_VENDA_ID]:
        canal = bot.get_channel(canal_id)
        if canal:
            async for mensagem in canal.history(limit=None):
                if mensagem.author == bot.user:
                    if f"<@{user_id}>" in mensagem.content or f"<@!{user_id}>" in mensagem.content:
                        novo = mensagem.content.replace(f"<@{user_id}>", f"[USUÁRIO REMOVIDO - {user_name}]").replace(f"<@!{user_id}>", f"[USUÁRIO REMOVIDO - {user_name}]")
                        try:
                            await mensagem.edit(content=novo)
                            total_limpo += 1
                        except:
                            pass
    for canal_id in dados["canais"].values():
        canal = bot.get_channel(canal_id)
        if canal:
            async for mensagem in canal.history(limit=None):
                if mensagem.author == bot.user:
                    if f"<@{user_id}>" in mensagem.content or f"<@!{user_id}>" in mensagem.content:
                        novo = mensagem.content.replace(f"<@{user_id}>", f"[USUÁRIO REMOVIDO - {user_name}]").replace(f"<@!{user_id}>", f"[USUÁRIO REMOVIDO - {user_name}]")
                        try:
                            await mensagem.edit(content=novo)
                            total_limpo += 1
                        except:
                            pass
    if str(user_id) in dados["usuarios"]:
        dados["usuarios"][str(user_id)] = {
            "farms": [], "pagamentos": [], "dinheiro_sujo": 0,
            "nome": f"[REMOVIDO - {user_name}]",
            "removido_em": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "removido_por": "sistema",
            "transacoes_dinheiro_sujo": [],
            "vendas_drogas": []
        }
        salvar_dados()
    if str(user_id) in dados["canais"]:
        canal = bot.get_channel(dados["canais"][str(user_id)])
        if canal:
            try:
                await canal.delete(reason=f"Usuário {user_name} removido do sistema")
            except:
                pass
        del dados["canais"][str(user_id)]
        salvar_dados()
    return total_limpo

async def log_acao(acao, usuario, detalhes, cor=None):
    cores = {
        "criar_canal": 0x00ff00, "registrar_farm": 0x00ff00,
        "registrar_dinheiro_sujo": 0xff0000, "pagar": 0xffa500,
        "fechar_canal": 0xff0000, "fechar_caixa": 0xffa500,
        "reset_rank": 0xff0000, "info": 0x3498db, "admin": 0x9b59b6,
        "setar_admin": 0x9b59b6, "compra_venda": 0x00ff00,
        "usuario_removido": 0xff0000, "editar_farm": 0x3498db,
        "editar_dinheiro_sujo": 0x3498db, "venda_drogas": 0x9b59b6
    }
    cor_final = cores.get(acao, 0x3498db) if cor is None else cor
    canal_logs = bot.get_channel(CHAT_LOGS_ID)
    if canal_logs:
        embed = discord.Embed(title=f"LOG: {acao.upper()}", description=detalhes, color=cor_final, timestamp=datetime.now())
        if usuario:
            embed.set_author(name=usuario.name, icon_url=usuario.display_avatar.url)
        else:
            embed.set_author(name="Sistema")
        await canal_logs.send(embed=embed)

_canal_admin_logs = None

async def log_admin(titulo, descricao, cor=0xffa500):
    global _canal_admin_logs
    if _canal_admin_logs is None:
        categoria = bot.get_channel(CATEGORIA_ADMIN_LOGS)
        if categoria and isinstance(categoria, discord.CategoryChannel):
            canal_existente = discord.utils.get(categoria.text_channels, name="admin-logs")
            if not canal_existente:
                try:
                    canal_existente = await categoria.create_text_channel("admin-logs")
                except:
                    pass
            _canal_admin_logs = canal_existente
    if _canal_admin_logs:
        await _canal_admin_logs.send(embed=discord.Embed(title=titulo, description=descricao, color=cor, timestamp=datetime.now()))

bot = commands.Bot(command_prefix="!", intents=discord.Intents.all())

# ========= HELPERS DE CARGO =========
def tem_cargo(member, cargos_ids):
    if not hasattr(member, 'guild'):
        return False
    for cid in cargos_ids:
        cargo = member.guild.get_role(cid)
        if cargo and cargo in member.roles:
            return True
    return False

def is_admin(member) -> bool:
    return tem_cargo(member, CARGOS_ADMIN_IDS)

def is_membro(member) -> bool:
    return tem_cargo(member, [CARGO_MEMBRO_ID])

def pode_registrar_farm(member) -> bool:
    return tem_cargo(member, [CARGO_MEMBRO_ID])

def pode_vender_arma(member) -> bool:
    return tem_cargo(member, CARGO_VENDA_ARMA_IDS)

def pode_comprar_produto(member) -> bool:
    return tem_cargo(member, CARGO_COMPRA_PRODUTO_IDS)

def pode_registrar_acao(member) -> bool:
    return tem_cargo(member, CARGO_REGISTRAR_ACAO_IDS)

def pode_resetar_rank(member) -> bool:
    return tem_cargo(member, CARGO_RESET_RANK_IDS)

# ========= RANKING =========
async def atualizar_ranking():
    canal = bot.get_channel(CHAT_RANK_ID)
    if not canal:
        return
    async for msg in canal.history(limit=50):
        if msg.author == bot.user:
            await msg.delete()
    usuarios_data = []
    for uid, data in dados["usuarios"].items():
        if "removido_em" in data:
            continue
        try:
            user = await bot.fetch_user(int(uid))
            tot_chumbo    = sum(p["quantidade"] for f in data["farms"] for p in f.get("produtos", []) if p["produto"] == "CHUMBO")
            tot_capsula   = sum(p["quantidade"] for f in data["farms"] for p in f.get("produtos", []) if p["produto"] == "CAPSULA")
            tot_polvora   = sum(p["quantidade"] for f in data["farms"] for p in f.get("produtos", []) if p["produto"] == "POLVORA")
            tot_pag       = sum(p["valor"] for p in data["pagamentos"])
            qtd_pag       = len(data["pagamentos"])
            din_sujo      = data.get("dinheiro_sujo", 0)
            tot_drogas    = sum(v.get("dinheiro", 0) for v in data.get("vendas_drogas", []))
            usuarios_data.append({
                "nome": user.name, "user_id": uid,
                "total_chumbo": tot_chumbo, "total_capsula": tot_capsula,
                "total_polvora": tot_polvora, "total_pagamentos": tot_pag,
                "quantidade_pagamentos": qtd_pag, "dinheiro_sujo": din_sujo,
                "total_drogas": tot_drogas
            })
        except:
            continue

    def top5(key):
        return sorted(usuarios_data, key=lambda x: x[key], reverse=True)[:5]

    def linha(i, u, key, prefix=""):
        medal = '🥇' if i == 1 else '🥈' if i == 2 else '🥉' if i == 3 else f'{i}°'
        return f"{medal} **{u['nome']}** - {prefix}{u[key]:,}\n"

    emb = discord.Embed(title="RANKING GERAL", description=f"Atualizado em {datetime.now().strftime('%d/%m/%Y %H:%M')}", color=discord.Color.gold())

    for nome, key in [("ROTAS", "total_chumbo"), ("CAPSULA", "total_capsula"), ("POLVORA", "total_polvora")]:
        lista = top5(key)
        txt = "".join(linha(i, u, key) for i, u in enumerate(lista, 1) if u[key] > 0)
        emb.add_field(name=nome, value=txt or "Nenhum dado ainda", inline=False)

    lista_salario = top5("total_pagamentos")
    txt = "".join(f"{'🥇' if i==1 else '🥈' if i==2 else '🥉' if i==3 else f'{i}°'} **{u['nome']}** - R$ {u['total_pagamentos']:,.2f} ({u['quantidade_pagamentos']} pag.)\n" for i, u in enumerate(lista_salario, 1) if u["total_pagamentos"] > 0)
    emb.add_field(name="TOP SALÁRIO", value=txt or "Nenhum dado ainda", inline=False)

    lista_sujo = top5("dinheiro_sujo")
    txt = "".join(f"{'🥇' if i==1 else '🥈' if i==2 else '🥉' if i==3 else f'{i}°'} **{u['nome']}** - R$ {u['dinheiro_sujo']:,.2f}\n" for i, u in enumerate(lista_sujo, 1) if u["dinheiro_sujo"] > 0)
    emb.add_field(name="DINHEIRO SUJO", value=txt or "Nenhum dado ainda", inline=False)

    lista_drogas = top5("total_drogas")
    txt = "".join(f"{'🥇' if i==1 else '🥈' if i==2 else '🥉' if i==3 else f'{i}°'} **{u['nome']}** - R$ {u['total_drogas']:,.2f}\n" for i, u in enumerate(lista_drogas, 1) if u["total_drogas"] > 0)
    emb.add_field(name="VENDAS DE DROGAS", value=txt or "Nenhum dado ainda", inline=False)

    await canal.send(embed=emb, view=RankingView())

class RankingView(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Atualizar Ranking", style=discord.ButtonStyle.primary, emoji="🔄")
    async def atualizar(self, interaction: discord.Interaction, button: Button):
        await interaction.response.defer()
        await atualizar_ranking()
        await interaction.followup.send("Ranking atualizado!", ephemeral=True)

    @discord.ui.button(label="Resetar Ranking", style=discord.ButtonStyle.danger, emoji="⚠️")
    async def resetar(self, interaction: discord.Interaction, button: Button):
        if not pode_resetar_rank(interaction.user):
            await interaction.response.send_message("Apenas os cargos 00, 01 e 02 podem resetar o ranking.", ephemeral=True)
            return
        await interaction.response.send_message("⚠️ ATENÇÃO! Tem certeza que deseja resetar o ranking?", view=ConfirmarResetView(), ephemeral=True)

class ConfirmarResetView(View):
    def __init__(self):
        super().__init__(timeout=60)

    @discord.ui.button(label="Sim, resetar ranking", style=discord.ButtonStyle.danger, emoji="⚠️")
    async def confirmar(self, interaction: discord.Interaction, button: Button):
        await interaction.response.defer(ephemeral=True, thinking=True)
        await salvar_backup_completo(interaction.user.name)
        dados["usuarios"] = {}
        dados["caixa_semana"] = {}
        dados["dinheiro_sujo"] = {}
        salvar_dados()
        await log_acao("reset_rank", interaction.user, f"Ranking resetado por {interaction.user.mention}", 0xff0000)
        await log_admin("RANKING RESETADO", f"Admin: {interaction.user.mention}\nData: {datetime.now().strftime('%d/%m/%Y %H:%M')}", 0xff0000)
        await interaction.followup.send("Ranking resetado com sucesso!", ephemeral=True)
        await atualizar_ranking()
        self.stop()

    @discord.ui.button(label="Cancelar", style=discord.ButtonStyle.secondary, emoji="❌")
    async def cancelar(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_message("Reset cancelado.", ephemeral=True)
        self.stop()

# ========= MODAIS DE FARM =========

class DinheiroSujoModal(Modal, title="Registrar Dinheiro Sujo (C4)"):
    qtd_c4 = TextInput(label="Quantidade de C4 que pegaram do baú", placeholder="Ex: 5", required=True)
    valor_rendeu = TextInput(label="Valor que rendeu (R$)", placeholder="Ex: 5000", required=True)

    def __init__(self, user_id, user_name, canal):
        super().__init__()
        self.user_id = user_id
        self.user_name = user_name
        self.canal = canal

    async def on_submit(self, interaction: discord.Interaction):
        if not (is_admin(interaction.user) or is_membro(interaction.user)):
            await interaction.response.send_message("Você não tem permissão para registrar dinheiro sujo.", ephemeral=True)
            return
        await interaction.response.defer(ephemeral=True, thinking=True)
        try:
            qtd_c4 = int(self.qtd_c4.value.strip())
            valor = float(self.valor_rendeu.value.replace(",", "."))
        except ValueError:
            await interaction.followup.send("Valores inválidos!", ephemeral=True)
            return
        await interaction.followup.send("📸 Agora envie a **print do comprovante** aqui no canal.", ephemeral=True)
        def check(m):
            return m.author == interaction.user and m.channel == self.canal and m.attachments and any(a.content_type and a.content_type.startswith('image/') for a in m.attachments)
        try:
            msg = await bot.wait_for('message', timeout=60.0, check=check)
        except asyncio.TimeoutError:
            await interaction.followup.send("Tempo esgotado!", ephemeral=True)
            return
        imagem_url = msg.attachments[0].url
        if str(self.user_id) not in dados["usuarios"]:
            dados["usuarios"][str(self.user_id)] = {"farms": [], "pagamentos": [], "nome": self.user_name, "dinheiro_sujo": 0, "transacoes_dinheiro_sujo": [], "vendas_drogas": []}
        if "transacoes_dinheiro_sujo" not in dados["usuarios"][str(self.user_id)]:
            dados["usuarios"][str(self.user_id)]["transacoes_dinheiro_sujo"] = []
        transacao = {
            "qtd_c4": qtd_c4,
            "valor": valor,
            "data": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "print_url": imagem_url,
            "registrado_por": interaction.user.id
        }
        dados["usuarios"][str(self.user_id)]["transacoes_dinheiro_sujo"].append(transacao)
        dados["usuarios"][str(self.user_id)]["dinheiro_sujo"] = sum(t["valor"] for t in dados["usuarios"][str(self.user_id)]["transacoes_dinheiro_sujo"])
        salvar_dados()
        embed = discord.Embed(
            title="💰 DINHEIRO SUJO (C4) REGISTRADO",
            description=f"**Usuário:** <@{self.user_id}>\n**C4 do baú:** {qtd_c4}\n**Valor que rendeu:** R$ {valor:,.2f}\n**Registrado por:** {interaction.user.mention}",
            color=discord.Color.red(), timestamp=datetime.now()
        )
        embed.set_image(url=imagem_url)
        await self.canal.send(embed=embed)
        canal_registros = bot.get_channel(LOG_REGISTROS_ID)
        if canal_registros:
            await canal_registros.send(embed=embed)
        await interaction.followup.send(f"C4: {qtd_c4} | R$ {valor:,.2f} registrado como dinheiro sujo para {self.user_name}!", ephemeral=True)
        await log_acao("registrar_dinheiro_sujo", interaction.user, f"Usuário: {self.user_name}\nC4: {qtd_c4}\nValor: R$ {valor:,.2f}", 0xff0000)
        await atualizar_ranking()


class VendaDrogasModal(Modal, title="Registrar Venda de Drogas"):
    qtd_bau = TextInput(label="Quantidade que pegou do baú", placeholder="Ex: 50", required=True)
    total_vendas = TextInput(label="Total de vendas (quantidade)", placeholder="Ex: 48", required=True)
    sobrou = TextInput(label="O que sobrou", placeholder="Ex: 2", required=True)
    dinheiro = TextInput(label="Dinheiro arrecadado (R$)", placeholder="Ex: 9600", required=True)

    def __init__(self, user_id, user_name, canal):
        super().__init__()
        self.user_id = user_id
        self.user_name = user_name
        self.canal = canal

    async def on_submit(self, interaction: discord.Interaction):
        if not (is_admin(interaction.user) or is_membro(interaction.user)):
            await interaction.response.send_message("Você não tem permissão para registrar vendas de drogas.", ephemeral=True)
            return
        await interaction.response.defer(ephemeral=True, thinking=True)
        try:
            qtd_bau = int(self.qtd_bau.value.strip())
            total_vendas = int(self.total_vendas.value.strip())
            sobrou = int(self.sobrou.value.strip())
            dinheiro = float(self.dinheiro.value.replace(",", "."))
        except ValueError:
            await interaction.followup.send("Valores inválidos!", ephemeral=True)
            return
        await interaction.followup.send("📸 Agora envie a **print do comprovante** aqui no canal.", ephemeral=True)
        def check(m):
            return m.author == interaction.user and m.channel == self.canal and m.attachments and any(a.content_type and a.content_type.startswith('image/') for a in m.attachments)
        try:
            msg = await bot.wait_for('message', timeout=60.0, check=check)
        except asyncio.TimeoutError:
            await interaction.followup.send("Tempo esgotado!", ephemeral=True)
            return
        imagem_url = msg.attachments[0].url
        if str(self.user_id) not in dados["usuarios"]:
            dados["usuarios"][str(self.user_id)] = {"farms": [], "pagamentos": [], "nome": self.user_name, "dinheiro_sujo": 0, "transacoes_dinheiro_sujo": [], "vendas_drogas": []}
        if "vendas_drogas" not in dados["usuarios"][str(self.user_id)]:
            dados["usuarios"][str(self.user_id)]["vendas_drogas"] = []
        registro = {
            "qtd_bau": qtd_bau,
            "total_vendas": total_vendas,
            "sobrou": sobrou,
            "dinheiro": dinheiro,
            "data": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "print_url": imagem_url,
            "registrado_por": interaction.user.id
        }
        dados["usuarios"][str(self.user_id)]["vendas_drogas"].append(registro)
        salvar_dados()
        embed = discord.Embed(
            title="💊 VENDA DE DROGAS REGISTRADA",
            description=f"**Usuário:** <@{self.user_id}>\n**Do baú:** {qtd_bau}\n**Total de vendas:** {total_vendas}\n**Sobrou:** {sobrou}\n**Dinheiro:** R$ {dinheiro:,.2f}\n**Registrado por:** {interaction.user.mention}",
            color=discord.Color.purple(), timestamp=datetime.now()
        )
        embed.set_image(url=imagem_url)
        await self.canal.send(embed=embed)
        canal_registros = bot.get_channel(LOG_REGISTROS_ID)
        if canal_registros:
            await canal_registros.send(embed=embed)
        await interaction.followup.send(f"Venda de drogas registrada! Dinheiro: R$ {dinheiro:,.2f}", ephemeral=True)
        await log_acao("venda_drogas", interaction.user, f"Usuário: {self.user_name}\nDinheiro: R$ {dinheiro:,.2f}", 0x9b59b6)
        await atualizar_ranking()


class FarmProdutosModal(Modal, title="Registrar Farm"):
    rotas = TextInput(label="Quantas rotas fez", placeholder="Ex: 5", required=True)
    corpo_rifle_normal   = TextInput(label="Corpo de Rifle Normal", placeholder="Ex: 10", required=False)
    corpo_rifle_especial = TextInput(label="Corpo de Rifle Especial", placeholder="Ex: 5", required=False)
    aluminio             = TextInput(label="Alumínio", placeholder="Ex: 200", required=False)
    chapa_metal          = TextInput(label="Chapa de Metal", placeholder="Ex: 30", required=False)

    def __init__(self, user_id, user_name, canal):
        super().__init__()
        self.user_id = user_id
        self.user_name = user_name
        self.canal = canal

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True, thinking=True)
        try:
            rotas = int(self.rotas.value.strip())
        except ValueError:
            await interaction.followup.send("Número de rotas inválido!", ephemeral=True)
            return
        produtos = []
        mapa_campos = [
            (self.corpo_rifle_normal,   "CORPO DE RIFLE NORMAL"),
            (self.corpo_rifle_especial, "CORPO DE RIFLE ESPECIAL"),
            (self.aluminio,             "ALUMINIO"),
            (self.chapa_metal,          "CHAPA DE METAL"),
        ]
        for campo, nome in mapa_campos:
            if campo.value and campo.value.strip():
                try:
                    qtd = int(campo.value.strip())
                    if qtd > 0:
                        produtos.append({"produto": nome, "quantidade": qtd})
                except ValueError:
                    pass
        self._rotas = rotas
        self._produtos_parciais = produtos
        view = FarmProdutos2View(self.user_id, self.user_name, self.canal, rotas, produtos)
        await interaction.followup.send("Preencha os campos restantes:", view=view, ephemeral=True)


class FarmProdutos2View(View):
    def __init__(self, user_id, user_name, canal, rotas, produtos_parciais):
        super().__init__(timeout=120)
        self.user_id = user_id
        self.user_name = user_name
        self.canal = canal
        self.rotas = rotas
        self.produtos_parciais = produtos_parciais

    @discord.ui.button(label="Continuar → Mais Itens", style=discord.ButtonStyle.primary, emoji="➡️")
    async def continuar(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_modal(FarmProdutos2Modal(self.user_id, self.user_name, self.canal, self.rotas, self.produtos_parciais))


class FarmProdutos2Modal(Modal, title="Farm - Itens Adicionais"):
    borracha       = TextInput(label="Borracha", placeholder="Ex: 50", required=False)
    corpo_pistola  = TextInput(label="Corpo de Pistola", placeholder="Ex: 20", required=False)
    corpo_sub      = TextInput(label="Corpo de Sub", placeholder="Ex: 15", required=False)

    def __init__(self, user_id, user_name, canal, rotas, produtos_parciais):
        super().__init__()
        self.user_id = user_id
        self.user_name = user_name
        self.canal = canal
        self.rotas = rotas
        self.produtos_parciais = produtos_parciais

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True, thinking=True)
        novos = []
        for campo, nome in [
            (self.borracha,      "BORRACHA"),
            (self.corpo_pistola, "CORPO DE PISTOLA"),
            (self.corpo_sub,     "CORPO DE SUB"),
        ]:
            if campo.value and campo.value.strip():
                try:
                    qtd = int(campo.value.strip())
                    if qtd > 0:
                        novos.append({"produto": nome, "quantidade": qtd})
                except ValueError:
                    pass
        produtos = self.produtos_parciais + novos
        await interaction.followup.send("📸 Agora envie a **print da farm** aqui no canal.", ephemeral=True)
        def check(m):
            return m.author == interaction.user and m.channel == self.canal and m.attachments and any(a.content_type and a.content_type.startswith('image/') for a in m.attachments)
        try:
            msg = await bot.wait_for('message', timeout=60.0, check=check)
        except asyncio.TimeoutError:
            await interaction.followup.send("Tempo esgotado!", ephemeral=True)
            return
        imagem_url = msg.attachments[0].url
        if str(self.user_id) not in dados["usuarios"]:
            dados["usuarios"][str(self.user_id)] = {"farms": [], "pagamentos": [], "nome": self.user_name, "dinheiro_sujo": 0, "transacoes_dinheiro_sujo": [], "vendas_drogas": []}
        registro = {
            "rotas": self.rotas,
            "produtos": produtos,
            "data": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "print_url": imagem_url,
            "validado": True,
            "farm_id": len(dados["usuarios"][str(self.user_id)]["farms"]) + 1
        }
        dados["usuarios"][str(self.user_id)]["farms"].append(registro)
        salvar_dados()
        embed = discord.Embed(
            title="FARM REGISTRADA COM SUCESSO",
            description=f"**Usuário:** <@{self.user_id}>\n**Rotas feitas:** {self.rotas}",
            color=discord.Color.green()
        )
        if produtos:
            desc = "".join(f"🔩 **{p['produto']}:** {p['quantidade']}\n" for p in produtos)
            embed.add_field(name="Itens coletados", value=desc, inline=False)
        embed.add_field(name="Data", value=datetime.now().strftime("%d/%m/%Y às %H:%M"), inline=False)
        embed.set_image(url=imagem_url)
        await self.canal.send(embed=embed)
        canal_registros = bot.get_channel(LOG_REGISTROS_ID)
        if canal_registros:
            await canal_registros.send(embed=embed)
        await interaction.followup.send(embed=embed, ephemeral=True)
        await log_acao("registrar_farm", interaction.user, f"Rotas: {self.rotas}\nProdutos: {len(produtos)} tipos")
        await log_admin("NOVA FARM", f"Usuário: {interaction.user.mention}\nRotas: {self.rotas}", 0x00ff00)
        await atualizar_ranking()


class PagamentoFarmModal(Modal, title="Registrar Pagamento"):
    valor = TextInput(label="Valor do Pagamento (R$)", placeholder="Ex: 500", required=True)

    def __init__(self, user_id, user_name, canal):
        super().__init__()
        self.user_id = user_id
        self.user_name = user_name
        self.canal = canal

    async def on_submit(self, interaction: discord.Interaction):
        if not is_admin(interaction.user):
            await interaction.response.send_message("Apenas administradores podem registrar pagamentos.", ephemeral=True)
            return
        await interaction.response.defer(ephemeral=True, thinking=True)
        try:
            valor = float(self.valor.value.replace(",", "."))
        except ValueError:
            await interaction.followup.send("Valor inválido!", ephemeral=True)
            return
        await interaction.followup.send("📸 Agora envie a **print do comprovante** aqui no canal.", ephemeral=True)
        def check(m):
            return m.author == interaction.user and m.channel == self.canal and m.attachments and any(a.content_type and a.content_type.startswith('image/') for a in m.attachments)
        try:
            msg = await bot.wait_for('message', timeout=60.0, check=check)
        except asyncio.TimeoutError:
            await interaction.followup.send("Tempo esgotado!", ephemeral=True)
            return
        imagem_url = msg.attachments[0].url
        if str(self.user_id) not in dados["usuarios"]:
            dados["usuarios"][str(self.user_id)] = {"farms": [], "pagamentos": [], "nome": self.user_name, "dinheiro_sujo": 0, "transacoes_dinheiro_sujo": [], "vendas_drogas": []}
        dados["usuarios"][str(self.user_id)]["pagamentos"].append({
            "valor": valor, "data": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "admin": interaction.user.id, "admin_nome": interaction.user.name,
            "tipo": "Pagamento", "print_url": imagem_url
        })
        salvar_dados()
        embed = discord.Embed(
            title="PAGAMENTO REGISTRADO",
            description=f"**Usuário:** <@{self.user_id}>\n**Valor:** R$ {valor:,.2f}\n**Admin:** {interaction.user.mention}",
            color=discord.Color.green(), timestamp=datetime.now()
        ).set_image(url=imagem_url)
        await self.canal.send(embed=embed)
        canal_registros = bot.get_channel(LOG_REGISTROS_ID)
        if canal_registros:
            await canal_registros.send(embed=embed)
        await interaction.followup.send(f"Pagamento de R$ {valor:,.2f} registrado!", ephemeral=True)
        await log_acao("pagar", interaction.user, f"Usuário: {self.user_name}\nValor: R$ {valor:,.2f}", 0xffa500)
        await atualizar_ranking()


# ========= FECHAR CAIXA (ESCOLHER TIPO) =========

class EscolherTipoFechamentoView(View):
    def __init__(self, user_id, user_name, canal):
        super().__init__(timeout=120)
        self.user_id = user_id
        self.user_name = user_name
        self.canal = canal
        self.add_item(TipoFechamentoSelect(user_id, user_name, canal))


class TipoFechamentoSelect(Select):
    def __init__(self, user_id, user_name, canal):
        self.user_id = str(user_id)
        self.user_name = user_name
        self.canal = canal
        options = [
            discord.SelectOption(label="💊 Drogas", description="Fechar caixa de vendas de drogas", value="drogas"),
            discord.SelectOption(label="💰 Dinheiro Sujo (C4)", description="Fechar caixa de dinheiro sujo", value="dinheiro_sujo"),
            discord.SelectOption(label="📦 Farm de Produtos", description="Fechar caixa de farm", value="farm"),
        ]
        super().__init__(placeholder="Qual tipo de caixa fechar?", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        tipo = self.values[0]
        user_data = dados["usuarios"].get(self.user_id, {})

        if tipo == "dinheiro_sujo":
            total_sujo = user_data.get("dinheiro_sujo", 0.0)
            if total_sujo <= 0:
                await interaction.response.send_message("Nenhum dinheiro sujo acumulado.", ephemeral=True)
                return
            lavagem = total_sujo * 0.25
            restante = total_sujo - lavagem
            faccao = restante * 0.60
            membro_base = restante * 0.40
            embed = discord.Embed(title="RESUMO - DINHEIRO SUJO", color=discord.Color.orange())
            embed.add_field(name="Total Farmado", value=f"R$ {total_sujo:,.2f}", inline=False)
            embed.add_field(name="Lavagem (25%)", value=f"R$ {lavagem:,.2f}", inline=True)
            embed.add_field(name="Facção (60%)", value=f"R$ {faccao:,.2f}", inline=True)
            embed.add_field(name="Membro Base (40%)", value=f"R$ {membro_base:,.2f}", inline=True)
            view = FechamentoSummaryView(self.user_id, self.user_name, self.canal, total_sujo, lavagem, faccao, membro_base, "dinheiro_sujo")
            await interaction.response.send_message(embed=embed, view=view)

        elif tipo == "drogas":
            vendas = user_data.get("vendas_drogas", [])
            if not vendas:
                await interaction.response.send_message("Nenhuma venda de droga registrada.", ephemeral=True)
                return
            total = sum(v.get("dinheiro", 0) for v in vendas)
            embed = discord.Embed(title="RESUMO - DROGAS", color=discord.Color.purple())
            embed.add_field(name="Total Arrecadado", value=f"R$ {total:,.2f}", inline=False)
            embed.add_field(name="Registros", value=f"{len(vendas)} vendas", inline=False)
            view = FechamentoDrogasView(self.user_id, self.user_name, self.canal, total, vendas)
            await interaction.response.send_message(embed=embed, view=view)

        elif tipo == "farm":
            farms = user_data.get("farms", [])
            if not farms:
                await interaction.response.send_message("Nenhuma farm registrada.", ephemeral=True)
                return
            total_rotas = sum(f.get("rotas", 0) for f in farms)
            embed = discord.Embed(title="RESUMO - FARM DE PRODUTOS", color=discord.Color.green())
            embed.add_field(name="Total de Rotas", value=str(total_rotas), inline=False)
            embed.add_field(name="Registros", value=f"{len(farms)} farms", inline=False)
            view = FechamentoFarmView(self.user_id, self.user_name, self.canal, total_rotas, farms)
            await interaction.response.send_message(embed=embed, view=view)


class FechamentoSummaryView(View):
    def __init__(self, user_id, user_name, canal, total_sujo, lavagem, faccao, membro_base, tipo):
        super().__init__(timeout=300)
        self.user_id = user_id
        self.user_name = user_name
        self.canal = canal
        self.total_sujo = total_sujo
        self.lavagem = lavagem
        self.faccao = faccao
        self.membro_base = membro_base
        self.tipo = tipo

    @discord.ui.button(label="Continuar Fechamento", style=discord.ButtonStyle.success, emoji="✅")
    async def continuar(self, interaction: discord.Interaction, button: Button):
        if not is_admin(interaction.user):
            await interaction.response.send_message("Apenas administradores!", ephemeral=True)
            return
        modal = FechamentoCaixaModal(self.user_id, self.user_name, self.canal, self.total_sujo, self.lavagem, self.faccao, self.membro_base)
        await interaction.response.send_modal(modal)


class FechamentoDrogasView(View):
    def __init__(self, user_id, user_name, canal, total, vendas):
        super().__init__(timeout=300)
        self.user_id = user_id
        self.user_name = user_name
        self.canal = canal
        self.total = total
        self.vendas = vendas

    @discord.ui.button(label="Registrar Pagamento de Drogas", style=discord.ButtonStyle.success, emoji="✅")
    async def pagar(self, interaction: discord.Interaction, button: Button):
        if not is_admin(interaction.user):
            await interaction.response.send_message("Apenas administradores!", ephemeral=True)
            return
        await interaction.response.defer(ephemeral=True, thinking=True)
        await interaction.followup.send("📸 Envie a **print do comprovante**.", ephemeral=True)
        def check(m):
            return m.author == interaction.user and m.channel == self.canal and m.attachments and any(a.content_type and a.content_type.startswith('image/') for a in m.attachments)
        try:
            msg = await bot.wait_for('message', timeout=60.0, check=check)
        except asyncio.TimeoutError:
            await interaction.followup.send("Tempo esgotado!", ephemeral=True)
            return
        imagem_url = msg.attachments[0].url
        if str(self.user_id) not in dados["usuarios"]:
            dados["usuarios"][str(self.user_id)] = {"farms": [], "pagamentos": [], "nome": self.user_name, "dinheiro_sujo": 0, "transacoes_dinheiro_sujo": [], "vendas_drogas": []}
        dados["usuarios"][str(self.user_id)]["pagamentos"].append({
            "valor": self.total, "data": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "admin": interaction.user.id, "admin_nome": interaction.user.name,
            "tipo": "Fechamento Drogas", "print_url": imagem_url
        })
        dados["usuarios"][str(self.user_id)]["vendas_drogas"] = []
        salvar_dados()
        embed = discord.Embed(
            title="FECHAMENTO DE CAIXA - DROGAS",
            description=f"**{self.user_name}** fechou a caixa de drogas!\n**Total:** R$ {self.total:,.2f}\n**Admin:** {interaction.user.mention}",
            color=discord.Color.purple(), timestamp=datetime.now()
        ).set_image(url=imagem_url)
        await self.canal.send(embed=embed)
        await interaction.followup.send(f"Caixa de drogas fechada! Total: R$ {self.total:,.2f}", ephemeral=True)
        await log_acao("fechar_caixa", interaction.user, f"Usuário: {self.user_name}\nTipo: Drogas\nValor: R$ {self.total:,.2f}", 0x9b59b6)
        await atualizar_ranking()


class FechamentoFarmView(View):
    def __init__(self, user_id, user_name, canal, total_rotas, farms):
        super().__init__(timeout=300)
        self.user_id = user_id
        self.user_name = user_name
        self.canal = canal
        self.total_rotas = total_rotas
        self.farms = farms

    @discord.ui.button(label="Registrar Pagamento de Farm", style=discord.ButtonStyle.success, emoji="✅")
    async def pagar(self, interaction: discord.Interaction, button: Button):
        if not is_admin(interaction.user):
            await interaction.response.send_message("Apenas administradores!", ephemeral=True)
            return
        await interaction.response.send_modal(FechamentoFarmModal(self.user_id, self.user_name, self.canal, self.total_rotas))


class FechamentoFarmModal(Modal, title="Fechar Caixa - Farm"):
    valor_pagar = TextInput(label="Valor a pagar (R$)", placeholder="Ex: 1500", required=True)
    observacao = TextInput(label="Observação", required=False, style=discord.TextStyle.long)

    def __init__(self, user_id, user_name, canal, total_rotas):
        super().__init__()
        self.user_id = user_id
        self.user_name = user_name
        self.canal = canal
        self.total_rotas = total_rotas

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True, thinking=True)
        try:
            valor = float(self.valor_pagar.value.replace(",", "."))
        except ValueError:
            await interaction.followup.send("Valor inválido!", ephemeral=True)
            return
        await interaction.followup.send("📸 Envie a **print do comprovante**.", ephemeral=True)
        def check(m):
            return m.author == interaction.user and m.channel == self.canal and m.attachments and any(a.content_type and a.content_type.startswith('image/') for a in m.attachments)
        try:
            msg = await bot.wait_for('message', timeout=60.0, check=check)
        except asyncio.TimeoutError:
            await interaction.followup.send("Tempo esgotado!", ephemeral=True)
            return
        imagem_url = msg.attachments[0].url
        if str(self.user_id) not in dados["usuarios"]:
            dados["usuarios"][str(self.user_id)] = {"farms": [], "pagamentos": [], "nome": self.user_name, "dinheiro_sujo": 0, "transacoes_dinheiro_sujo": [], "vendas_drogas": []}
        dados["usuarios"][str(self.user_id)]["pagamentos"].append({
            "valor": valor, "data": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "admin": interaction.user.id, "admin_nome": interaction.user.name,
            "tipo": "Fechamento Farm", "print_url": imagem_url
        })
        dados["usuarios"][str(self.user_id)]["farms"] = []
        salvar_dados()
        embed = discord.Embed(
            title="FECHAMENTO DE CAIXA - FARM",
            description=f"**{self.user_name}** fechou a farm!\n**Total de Rotas:** {self.total_rotas}\n**Valor Pago:** R$ {valor:,.2f}\n**Admin:** {interaction.user.mention}",
            color=discord.Color.green(), timestamp=datetime.now()
        )
        if self.observacao.value:
            embed.add_field(name="💌 Observação", value=self.observacao.value, inline=False)
        embed.set_image(url=imagem_url)
        await self.canal.send(embed=embed)
        await interaction.followup.send(f"Farm fechada! R$ {valor:,.2f} registrado.", ephemeral=True)
        await log_acao("fechar_caixa", interaction.user, f"Usuário: {self.user_name}\nTipo: Farm\nRotas: {self.total_rotas}\nValor: R$ {valor:,.2f}", 0x00ff00)
        await atualizar_ranking()


class FechamentoCaixaModal(Modal, title="Finalizar Fechamento - Dinheiro Sujo"):
    meta_farm = TextInput(label="Meta de Farm (Sim/Não)", placeholder="Digite Sim ou Não", required=True)
    bonus = TextInput(label="Bônus (R$) - Opcional", placeholder="Ex: 500 (deixe 0 se não houver)", required=False, default="0")
    observacao = TextInput(label="Observação", placeholder="Deixe uma mensagem para o usuário...", required=False, style=discord.TextStyle.long)

    def __init__(self, user_id, user_name, canal, total_sujo, lavagem, faccao, membro_base):
        super().__init__()
        self.user_id = user_id
        self.user_name = user_name
        self.canal = canal
        self.total_sujo = total_sujo
        self.lavagem = lavagem
        self.faccao = faccao
        self.membro_base = membro_base

    async def on_submit(self, interaction: discord.Interaction):
        if not is_admin(interaction.user):
            await interaction.response.send_message("Apenas administradores!", ephemeral=True)
            return
        await interaction.response.defer(ephemeral=True, thinking=True)
        meta = self.meta_farm.value.strip().lower()
        if meta not in ["sim", "não", "nao"]:
            await interaction.followup.send("Meta deve ser Sim/Não!", ephemeral=True)
            return
        meta = "Sim" if meta == "sim" else "Não"
        bonus_str = self.bonus.value.strip() or "0"
        try:
            bonus_valor = float(bonus_str.replace(",", "."))
        except ValueError:
            await interaction.followup.send("Bônus inválido!", ephemeral=True)
            return
        obs = self.observacao.value.strip() if self.observacao.value else None
        pagamento_final = self.membro_base + bonus_valor
        await interaction.followup.send("📸 Agora envie a **print do comprovante** aqui no canal.", ephemeral=True)
        def check(m):
            return m.author == interaction.user and m.channel == self.canal and m.attachments and any(a.content_type and a.content_type.startswith('image/') for a in m.attachments)
        try:
            msg = await bot.wait_for('message', timeout=60.0, check=check)
        except asyncio.TimeoutError:
            await interaction.followup.send("Tempo esgotado!", ephemeral=True)
            return
        imagem_url = msg.attachments[0].url
        if str(self.user_id) not in dados["usuarios"]:
            dados["usuarios"][str(self.user_id)] = {"farms": [], "pagamentos": [], "nome": self.user_name, "dinheiro_sujo": 0, "transacoes_dinheiro_sujo": [], "vendas_drogas": []}
        user_data = dados["usuarios"][str(self.user_id)]
        if pagamento_final > 0:
            user_data["pagamentos"].append({
                "valor": pagamento_final, "data": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "admin": interaction.user.id, "admin_nome": interaction.user.name,
                "tipo": "Fechamento de Caixa Semanal",
                "detalhes": {"total_sujo": self.total_sujo, "lavagem": self.lavagem, "faccao": self.faccao, "membro_base": self.membro_base, "bonus": bonus_valor},
                "print_url": imagem_url
            })
        user_data["dinheiro_sujo"] = 0
        user_data["transacoes_dinheiro_sujo"] = []
        fechamento = {
            "data": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "admin": interaction.user.name, "admin_id": interaction.user.id,
            "usuario": self.user_name, "usuario_id": self.user_id,
            "meta_farm": meta,
            "dinheiro_sujo": {"total": self.total_sujo, "lavagem": self.lavagem, "faccao": self.faccao, "membro_base": self.membro_base, "bonus": bonus_valor, "pago": pagamento_final},
            "print_url": imagem_url, "observacao": obs
        }
        if str(self.user_id) not in dados["caixa_semana"]:
            dados["caixa_semana"][str(self.user_id)] = []
        dados["caixa_semana"][str(self.user_id)].append(fechamento)
        salvar_dados()
        embed = discord.Embed(title="FECHAMENTO DE CAIXA SEMANAL - DINHEIRO SUJO", description=f"**{self.user_name}** fechou a semana!", color=discord.Color.orange(), timestamp=datetime.now())
        embed.add_field(name="Meta de Farm", value=meta, inline=False)
        embed.add_field(name="Total Farmado", value=f"R$ {self.total_sujo:,.2f}", inline=False)
        embed.add_field(name="Lavagem (25%)", value=f"R$ {self.lavagem:,.2f}", inline=True)
        embed.add_field(name="Facção (60%)", value=f"R$ {self.faccao:,.2f}", inline=True)
        embed.add_field(name="Membro Base (40%)", value=f"R$ {self.membro_base:,.2f}", inline=True)
        if bonus_valor > 0:
            embed.add_field(name="Bônus", value=f"R$ {bonus_valor:,.2f}", inline=True)
        embed.add_field(name="💰 Pagamento Final", value=f"R$ {pagamento_final:,.2f}", inline=False)
        embed.add_field(name="Responsável", value=interaction.user.mention, inline=False)
        if obs:
            embed.add_field(name="💌 Mensagem", value=obs, inline=False)
        embed.set_image(url=imagem_url)
        await self.canal.send(embed=embed)
        canal_registros = bot.get_channel(LOG_REGISTROS_ID)
        if canal_registros:
            await canal_registros.send(embed=embed)
        await interaction.followup.send(f"Pagamento de R$ {pagamento_final:,.2f} registrado!", ephemeral=True)
        await log_acao("fechar_caixa", interaction.user, f"Usuário: {self.user_name}\nPagamento: R$ {pagamento_final}", 0xffa500)
        await atualizar_ranking()
        # ========= COMPRA/VENDA =========
class VendaArmaModal(Modal, title="Venda de Arma"):
    tipo_arma   = TextInput(label="Tipo de Arma", placeholder="Ex: Rifle AK, Pistola Glock...", required=True)
    quantidade  = TextInput(label="Quantidade", placeholder="Ex: 10", required=True)
    valor_total = TextInput(label="Valor Total (R$)", placeholder="Ex: 5000", required=True)
    faccao      = TextInput(label="Facção Compradora", placeholder="Ex: Primeiro Comando", required=True)
    responsavel = TextInput(label="Responsável pela Venda", placeholder="Ex: @usuario ou nome", required=True)

    async def on_submit(self, interaction: discord.Interaction):
        if not pode_vender_arma(interaction.user):
            await interaction.response.send_message("Você não tem permissão para registrar vendas de arma.", ephemeral=True)
            return
        await interaction.response.defer(ephemeral=True, thinking=True)
        try:
            qtd = int(self.quantidade.value)
            valor = float(self.valor_total.value.replace(",", "."))
        except ValueError:
            await interaction.followup.send("Quantidade ou valor inválidos!", ephemeral=True)
            return
        await interaction.followup.send("📸 Agora envie a **print do comprovante da venda**.", ephemeral=True)
        def check(m):
            return m.author == interaction.user and m.channel == interaction.channel and m.attachments and any(a.content_type and a.content_type.startswith('image/') for a in m.attachments)
        try:
            msg = await bot.wait_for('message', timeout=60.0, check=check)
        except asyncio.TimeoutError:
            await interaction.followup.send("Tempo esgotado!", ephemeral=True)
            return
        imagem_url = msg.attachments[0].url
        dados_log = {
            "Tipo": "VENDA DE ARMA", "Arma": self.tipo_arma.value,
            "Quantidade": f"{qtd:,}", "Valor Total": f"R$ {valor:,.2f}",
            "Facção Compradora": self.faccao.value, "Responsável": self.responsavel.value,
            "Registrado por": interaction.user.mention
        }
        await criar_canal_compra_venda_log("venda-arma", dados_log)
        dados["compras_vendas"].append({
            "tipo": "venda_arma", "arma": self.tipo_arma.value,
            "quantidade": qtd, "valor_total": valor, "faccao_compradora": self.faccao.value,
            "responsavel": self.responsavel.value, "registrado_por": interaction.user.id,
            "data": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "print_url": imagem_url
        })
        salvar_dados()
        await interaction.followup.send(f"✅ Venda de **{qtd}x {self.tipo_arma.value}** registrada! Valor: R$ {valor:,.2f}", ephemeral=True)
        await log_acao("compra_venda", interaction.user, f"Venda Arma: {qtd}x {self.tipo_arma.value} - R$ {valor} - {self.faccao.value}", 0x00ff00)


class CompraModal(Modal, title="Compra de Produto"):
    quantidade      = TextInput(label="Quantidade", placeholder="Ex: 1000", required=True)
    produto         = TextInput(label="Produto", placeholder="Ex: Munição", required=True)
    valor_total     = TextInput(label="Valor Total (R$)", placeholder="Ex: 500", required=True)
    faccao_vendedora = TextInput(label="Facção Vendedora", placeholder="Ex: Primeiro Comando", required=True)
    responsavel     = TextInput(label="Responsável pela Compra", placeholder="Ex: @usuario ou nome", required=True)

    async def on_submit(self, interaction: discord.Interaction):
        if not pode_comprar_produto(interaction.user):
            await interaction.response.send_message("Você não tem permissão para registrar compras.", ephemeral=True)
            return
        await interaction.response.defer(ephemeral=True, thinking=True)
        try:
            qtd = int(self.quantidade.value)
            valor = float(self.valor_total.value.replace(",", "."))
        except:
            await interaction.followup.send("Valores inválidos!", ephemeral=True)
            return
        await interaction.followup.send("📸 Agora envie a **print do comprovante da compra**.", ephemeral=True)
        def check(m):
            return m.author == interaction.user and m.channel == interaction.channel and m.attachments and any(a.content_type and a.content_type.startswith('image/') for a in m.attachments)
        try:
            msg = await bot.wait_for('message', timeout=60.0, check=check)
        except asyncio.TimeoutError:
            await interaction.followup.send("Tempo esgotado!", ephemeral=True)
            return
        imagem_url = msg.attachments[0].url
        await criar_canal_compra_venda_log("compra", {
            "Tipo": "COMPRA", "Quantidade": f"{qtd:,}", "Produto": self.produto.value,
            "Valor Total": f"R$ {valor:,.2f}", "Facção Vendedora": self.faccao_vendedora.value,
            "Responsável": self.responsavel.value, "Registrado por": interaction.user.mention
        })
        dados["compras_vendas"].append({
            "tipo": "compra", "quantidade": qtd, "produto": self.produto.value,
            "valor_total": valor, "faccao_vendedora": self.faccao_vendedora.value,
            "responsavel": self.responsavel.value, "registrado_por": interaction.user.id,
            "data": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "print_url": imagem_url
        })
        salvar_dados()
        await interaction.followup.send("Compra registrada!", ephemeral=True)
        await log_acao("compra_venda", interaction.user, f"Compra: {qtd} x {self.produto.value} - R$ {valor}", 0x00ff00)


class CompraVendaView(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Venda de Arma", style=discord.ButtonStyle.success, emoji="🔫")
    async def venda(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_modal(VendaArmaModal())

    @discord.ui.button(label="Compra de Produto", style=discord.ButtonStyle.primary, emoji="🛒")
    async def compra(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_modal(CompraModal())


# ========= EDIÇÃO DE REGISTROS =========
class EditarRegistroSelect(Select):
    def __init__(self, user_id, user_name):
        self.user_id = str(user_id)
        self.user_name = user_name
        user_data = dados["usuarios"].get(self.user_id, {})
        farms = user_data.get("farms", [])
        options = []
        for idx, farm in enumerate(farms):
            farm_id = farm.get("farm_id", idx + 1)
            rotas = farm.get("rotas", 0)
            label = f"Farm #{farm_id} - {rotas} rotas"
            description = f"Data: {farm['data']}"[:100]
            options.append(discord.SelectOption(label=label, description=description, value=str(idx)))
        if not options:
            options.append(discord.SelectOption(label="Nenhum registro encontrado", value="none", default=True))
        super().__init__(placeholder="Selecione o registro de farm...", min_values=1, max_values=1, options=options[:25])

    async def callback(self, interaction: discord.Interaction):
        if self.values[0] == "none":
            await interaction.response.send_message("Nenhum registro de farm para editar.", ephemeral=True)
            return
        idx = int(self.values[0])
        user_data = dados["usuarios"].get(self.user_id)
        if not user_data or idx >= len(user_data["farms"]):
            await interaction.response.send_message("Registro não encontrado.", ephemeral=True)
            return
        farm = user_data["farms"][idx]
        modal = EditarFarmModal(self.user_id, self.user_name, interaction.channel, idx, farm)
        await interaction.response.send_modal(modal)


class EditarFarmModal(Modal, title="Editar Registro de Farm"):
    rotas = TextInput(label="Novas rotas", placeholder="Ex: 6", required=True)

    def __init__(self, user_id, user_name, canal, farm_index, farm_atual):
        super().__init__()
        self.user_id = user_id
        self.user_name = user_name
        self.canal = canal
        self.farm_index = farm_index
        self.farm_atual = farm_atual
        self.rotas.default = str(farm_atual.get("rotas", ""))

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True, thinking=True)
        try:
            novas_rotas = int(self.rotas.value.strip())
        except ValueError:
            await interaction.followup.send("Número de rotas inválido.", ephemeral=True)
            return
        await interaction.followup.send("📸 Envie a **nova print** comprovando a edição.", ephemeral=True)
        def check(m):
            return m.author == interaction.user and m.channel == self.canal and m.attachments and any(a.content_type and a.content_type.startswith('image/') for a in m.attachments)
        try:
            msg = await bot.wait_for('message', timeout=60.0, check=check)
        except asyncio.TimeoutError:
            await interaction.followup.send("Tempo esgotado. Edição cancelada.", ephemeral=True)
            return
        nova_imagem_url = msg.attachments[0].url
        user_data = dados["usuarios"].get(self.user_id)
        if not user_data or self.farm_index >= len(user_data["farms"]):
            await interaction.followup.send("Registro não encontrado.", ephemeral=True)
            return
        antigo = user_data["farms"][self.farm_index]
        novo_registro = {
            "rotas": novas_rotas,
            "produtos": antigo.get("produtos", []),
            "data": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "print_url": nova_imagem_url, "validado": True,
            "farm_id": antigo.get("farm_id", self.farm_index + 1)
        }
        user_data["farms"][self.farm_index] = novo_registro
        salvar_dados()
        embed = discord.Embed(
            title="✏️ REGISTRO DE FARM EDITADO",
            description=f"**Usuário:** <@{self.user_id}>\n**Farm ID:** {novo_registro['farm_id']}\n**Novas rotas:** {novas_rotas}",
            color=discord.Color.blue(), timestamp=datetime.now()
        )
        embed.set_image(url=nova_imagem_url)
        await self.canal.send(embed=embed)
        canal_registros = bot.get_channel(LOG_REGISTROS_ID)
        if canal_registros:
            await canal_registros.send(embed=embed)
        await interaction.followup.send(f"Registro #{novo_registro['farm_id']} editado com sucesso!", ephemeral=True)
        await log_acao("editar_farm", interaction.user, f"Usuário: {self.user_name}\nFarm ID: {novo_registro['farm_id']}\nNovas rotas: {novas_rotas}", 0x3498db)
        await atualizar_ranking()


class EditarDinheiroSujoSelect(Select):
    def __init__(self, user_id, user_name):
        self.user_id = str(user_id)
        self.user_name = user_name
        user_data = dados["usuarios"].get(self.user_id, {})
        transacoes = user_data.get("transacoes_dinheiro_sujo", [])
        options = []
        for idx, trans in enumerate(transacoes):
            valor = trans["valor"]
            data = trans["data"]
            label = f"R$ {valor:,.2f} - {data}"[:100]
            description = f"C4: {trans.get('qtd_c4', '?')}"[:100]
            options.append(discord.SelectOption(label=label, description=description, value=str(idx)))
        if not options:
            options.append(discord.SelectOption(label="Nenhum depósito encontrado", value="none", default=True))
        super().__init__(placeholder="Escolha o depósito de dinheiro sujo...", min_values=1, max_values=1, options=options[:25])

    async def callback(self, interaction: discord.Interaction):
        if self.values[0] == "none":
            await interaction.response.send_message("Nenhum depósito de dinheiro sujo para editar.", ephemeral=True)
            return
        idx = int(self.values[0])
        user_data = dados["usuarios"].get(self.user_id)
        if not user_data or idx >= len(user_data.get("transacoes_dinheiro_sujo", [])):
            await interaction.response.send_message("Registro não encontrado.", ephemeral=True)
            return
        trans = user_data["transacoes_dinheiro_sujo"][idx]
        modal = EditarDinheiroSujoModal(self.user_id, self.user_name, interaction.channel, idx, trans)
        await interaction.response.send_modal(modal)


class EditarDinheiroSujoModal(Modal, title="Editar Depósito de Dinheiro Sujo"):
    qtd_c4     = TextInput(label="Novo C4 do baú", placeholder="Ex: 5", required=True)
    novo_valor = TextInput(label="Novo valor (R$)", placeholder="Ex: 5000", required=True)

    def __init__(self, user_id, user_name, canal, trans_index, trans_atual):
        super().__init__()
        self.user_id = user_id
        self.user_name = user_name
        self.canal = canal
        self.trans_index = trans_index
        self.trans_atual = trans_atual
        self.qtd_c4.default = str(trans_atual.get("qtd_c4", ""))
        self.novo_valor.default = str(trans_atual["valor"])

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True, thinking=True)
        try:
            novo_c4 = int(self.qtd_c4.value.strip())
            novo_valor = float(self.novo_valor.value.replace(",", "."))
        except ValueError:
            await interaction.followup.send("Valores inválidos.", ephemeral=True)
            return
        await interaction.followup.send("📸 Envie a **nova print** do comprovante.", ephemeral=True)
        def check(m):
            return m.author == interaction.user and m.channel == self.canal and m.attachments and any(a.content_type and a.content_type.startswith('image/') for a in m.attachments)
        try:
            msg = await bot.wait_for('message', timeout=60.0, check=check)
        except asyncio.TimeoutError:
            await interaction.followup.send("Tempo esgotado.", ephemeral=True)
            return
        nova_imagem_url = msg.attachments[0].url
        user_data = dados["usuarios"].get(self.user_id)
        if not user_data or self.trans_index >= len(user_data.get("transacoes_dinheiro_sujo", [])):
            await interaction.followup.send("Registro não encontrado.", ephemeral=True)
            return
        antiga = user_data["transacoes_dinheiro_sujo"][self.trans_index]
        nova_trans = {
            "qtd_c4": novo_c4, "valor": novo_valor,
            "data": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "print_url": nova_imagem_url, "registrado_por": interaction.user.id
        }
        user_data["transacoes_dinheiro_sujo"][self.trans_index] = nova_trans
        user_data["dinheiro_sujo"] = sum(t["valor"] for t in user_data["transacoes_dinheiro_sujo"])
        salvar_dados()
        embed = discord.Embed(
            title="✏️ DEPÓSITO EDITADO",
            description=f"**Usuário:** <@{self.user_id}>\n**C4 antigo:** {antiga.get('qtd_c4','?')} → **Novo:** {novo_c4}\n**Valor antigo:** R$ {antiga['valor']:,.2f} → **Novo:** R$ {novo_valor:,.2f}",
            color=discord.Color.blue(), timestamp=datetime.now()
        )
        embed.set_image(url=nova_imagem_url)
        await self.canal.send(embed=embed)
        canal_registros = bot.get_channel(LOG_REGISTROS_ID)
        if canal_registros:
            await canal_registros.send(embed=embed)
        await interaction.followup.send(f"Depósito editado! Novo valor: R$ {novo_valor:,.2f}", ephemeral=True)
        await log_acao("editar_dinheiro_sujo", interaction.user, f"Usuário: {self.user_name}\nNovo valor: R$ {novo_valor:,.2f}", 0x3498db)
        await atualizar_ranking()


class EscolherTipoEdicaoView(View):
    def __init__(self, user_id, user_name):
        super().__init__(timeout=120)
        self.user_id = user_id
        self.user_name = user_name
        self.add_item(TipoEdicaoSelect(user_id, user_name))


class TipoEdicaoSelect(Select):
    def __init__(self, user_id, user_name):
        self.user_id = str(user_id)
        self.user_name = user_name
        options = [
            discord.SelectOption(label="📦 Farm", description="Editar um registro de farm", value="farm"),
            discord.SelectOption(label="💰 Dinheiro Sujo", description="Editar um depósito de dinheiro sujo", value="dinheiro_sujo"),
        ]
        super().__init__(placeholder="O que você deseja editar?", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        tipo = self.values[0]
        if tipo == "farm":
            select = EditarRegistroSelect(self.user_id, self.user_name)
            view = View(timeout=None)
            view.add_item(select)
            await interaction.response.send_message("Selecione o registro de farm que deseja editar:", view=view, ephemeral=True)
        else:
            select = EditarDinheiroSujoSelect(self.user_id, self.user_name)
            view = View(timeout=None)
            view.add_item(select)
            await interaction.response.send_message("Selecione o depósito de dinheiro sujo que deseja editar:", view=view, ephemeral=True)


async def enviar_historico_farms(interaction, user_id, user_name):
    user_data = dados["usuarios"].get(str(user_id), {})
    farms = user_data.get("farms", [])
    transacoes = user_data.get("transacoes_dinheiro_sujo", [])
    drogas = user_data.get("vendas_drogas", [])
    if not farms and not transacoes and not drogas:
        await interaction.followup.send("Você ainda não tem nenhum registro.", ephemeral=True)
        return
    embed = discord.Embed(title=f"📋 Histórico de Registros - {user_name}", color=0x2ecc71)
    todos = []
    for farm in farms:
        todos.append({"tipo": "farm", "data": farm["data"], "detalhes": farm})
    for trans in transacoes:
        todos.append({"tipo": "dinheiro_sujo", "data": trans["data"], "detalhes": trans})
    for v in drogas:
        todos.append({"tipo": "drogas", "data": v["data"], "detalhes": v})
    todos.sort(key=lambda x: x["data"], reverse=True)
    for registro in todos[:10]:
        tipo = registro["tipo"]
        detalhes = registro["detalhes"]
        if tipo == "farm":
            farm_id = detalhes.get("farm_id", "?")
            rotas = detalhes.get("rotas", 0)
            print_url = detalhes.get("print_url", "")
            valor = f"**Farm #{farm_id}** - {rotas} rotas"
            if print_url:
                valor += f"\n🖼️ [Ver print]({print_url})"
            embed.add_field(name=f"📦 Farm #{farm_id} ({registro['data']})", value=valor, inline=False)
        elif tipo == "dinheiro_sujo":
            valor_ds = detalhes["valor"]
            qtd_c4 = detalhes.get("qtd_c4", "?")
            print_url = detalhes.get("print_url", "")
            valor = f"💰 R$ {valor_ds:,.2f} | C4: {qtd_c4}"
            if print_url:
                valor += f"\n🖼️ [Ver print]({print_url})"
            embed.add_field(name=f"💵 Dinheiro Sujo ({registro['data']})", value=valor, inline=False)
        else:
            din = detalhes.get("dinheiro", 0)
            total_v = detalhes.get("total_vendas", 0)
            print_url = detalhes.get("print_url", "")
            valor = f"💊 R$ {din:,.2f} | {total_v} vendas"
            if print_url:
                valor += f"\n🖼️ [Ver print]({print_url})"
            embed.add_field(name=f"💊 Drogas ({registro['data']})", value=valor, inline=False)
    await interaction.followup.send(embed=embed, ephemeral=True)


# ========= CANAL PRIVADO DE FARM =========
class FarmChannelView(View):
    def __init__(self, user_id, user_name, canal_id):
        super().__init__(timeout=None)
        self.user_id = user_id
        self.user_name = user_name
        self.canal_id = canal_id

    @discord.ui.button(label="Farm Produtos", style=discord.ButtonStyle.success, emoji="📦", row=0)
    async def farm_produtos(self, interaction: discord.Interaction, button: Button):
        if not (is_admin(interaction.user) or is_membro(interaction.user)):
            await interaction.response.send_message("Apenas membros podem registrar farm.", ephemeral=True)
            return
        await interaction.response.send_modal(FarmProdutosModal(self.user_id, self.user_name, interaction.channel))

    @discord.ui.button(label="Farm Dinheiro Sujo", style=discord.ButtonStyle.danger, emoji="💰", row=0)
    async def farm_dinheiro_sujo(self, interaction: discord.Interaction, button: Button):
        if not (is_admin(interaction.user) or is_membro(interaction.user)):
            await interaction.response.send_message("Você não tem permissão para registrar dinheiro sujo.", ephemeral=True)
            return
        await interaction.response.send_modal(DinheiroSujoModal(self.user_id, self.user_name, interaction.channel))

    @discord.ui.button(label="Venda de Drogas", style=discord.ButtonStyle.secondary, emoji="💊", row=0)
    async def venda_drogas(self, interaction: discord.Interaction, button: Button):
        if not (is_admin(interaction.user) or is_membro(interaction.user)):
            await interaction.response.send_message("Você não tem permissão para registrar vendas de drogas.", ephemeral=True)
            return
        await interaction.response.send_modal(VendaDrogasModal(self.user_id, self.user_name, interaction.channel))

    @discord.ui.button(label="Editar Registro", style=discord.ButtonStyle.blurple, emoji="✏️", row=1)
    async def editar_registro(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.user_id and not is_admin(interaction.user):
            await interaction.response.send_message("Apenas o dono do canal ou admin pode editar.", ephemeral=True)
            return
        view = EscolherTipoEdicaoView(self.user_id, self.user_name)
        await interaction.response.send_message("Escolha o tipo de registro que deseja editar:", view=view, ephemeral=True)

    @discord.ui.button(label="Fechar Caixa", style=discord.ButtonStyle.danger, emoji="📊", row=1)
    async def fechar_caixa(self, interaction: discord.Interaction, button: Button):
        if not is_admin(interaction.user):
            await interaction.response.send_message("Apenas administradores!", ephemeral=True)
            return
        view = EscolherTipoFechamentoView(self.user_id, self.user_name, interaction.channel)
        await interaction.response.send_message("Escolha qual tipo de caixa fechar:", view=view, ephemeral=True)

    @discord.ui.button(label="Mudar Nome", style=discord.ButtonStyle.secondary, emoji="✏️", row=1)
    async def mudar_nome(self, interaction: discord.Interaction, button: Button):
        if not is_admin(interaction.user):
            await interaction.response.send_message("Apenas administradores!", ephemeral=True)
            return
        await interaction.response.send_modal(MudarNomeModal(interaction.channel))

    @discord.ui.button(label="Histórico Caixa", style=discord.ButtonStyle.secondary, emoji="📜", row=2)
    async def historico_caixa(self, interaction: discord.Interaction, button: Button):
        if not is_admin(interaction.user):
            await interaction.response.send_message("Apenas administradores!", ephemeral=True)
            return
        await interaction.response.defer(ephemeral=True, thinking=True)
        fechamentos = dados["caixa_semana"].get(str(self.user_id), [])
        if not fechamentos:
            await interaction.followup.send("Nenhum fechamento.", ephemeral=True)
            return
        embed = discord.Embed(title="HISTÓRICO DE CAIXA", description=f"Últimos {min(10, len(fechamentos))} registros", color=discord.Color.blue())
        for fech in fechamentos[-10:]:
            data = datetime.strptime(fech["data"], "%Y-%m-%d %H:%M:%S").strftime("%d/%m/%Y")
            txt = f"Meta: {fech.get('meta_farm', '?')}\n"
            if "dinheiro_sujo" in fech:
                ds = fech["dinheiro_sujo"]
                txt += f"Farm Sujo: R$ {ds['total']:,.2f}\nLavagem: R$ {ds['lavagem']:,.2f}\nFacção: R$ {ds['faccao']:,.2f}\nMembro Base: R$ {ds['membro_base']:,.2f}"
                if ds.get('bonus', 0) > 0:
                    txt += f"\nBônus: R$ {ds['bonus']:,.2f}"
                txt += f"\n**Pago: R$ {ds['pago']:,.2f}**"
            if fech.get('observacao'):
                txt += f"\n💌 {fech['observacao']}"
            embed.add_field(name=f"📅 {data}", value=txt, inline=False)
        await interaction.followup.send(embed=embed, ephemeral=True)

    @discord.ui.button(label="Meus Registros", style=discord.ButtonStyle.primary, emoji="📋", row=2)
    async def meus_registros(self, interaction: discord.Interaction, button: Button):
        await interaction.response.defer(ephemeral=True)
        await enviar_historico_farms(interaction, self.user_id, self.user_name)

    @discord.ui.button(label="Reset Semanal", style=discord.ButtonStyle.danger, emoji="🔄", row=2)
    async def reset_semanal(self, interaction: discord.Interaction, button: Button):
        if not is_admin(interaction.user):
            await interaction.response.send_message("Apenas administradores!", ephemeral=True)
            return
        confirm_view = ConfirmResetSemanalView(self.user_id, self.user_name, interaction.channel)
        await interaction.response.send_message("⚠️ **Tem certeza que deseja resetar a semana?**", view=confirm_view, ephemeral=True)

    @discord.ui.button(label="Fechar Canal", style=discord.ButtonStyle.danger, emoji="🗑️", row=3)
    async def fechar_canal(self, interaction: discord.Interaction, button: Button):
        if not is_admin(interaction.user):
            await interaction.response.send_message("Apenas administradores!", ephemeral=True)
            return
        await interaction.response.send_message("⚠️ Tem certeza?", view=ConfirmarFechamentoView(self.user_id, interaction.channel), ephemeral=True)


class ConfirmResetSemanalView(View):
    def __init__(self, user_id, user_name, canal):
        super().__init__(timeout=60)
        self.user_id = user_id
        self.user_name = user_name
        self.canal = canal

    @discord.ui.button(label="Sim, resetar semana", style=discord.ButtonStyle.danger, emoji="✅")
    async def confirm(self, interaction: discord.Interaction, button: Button):
        await interaction.response.defer(ephemeral=True, thinking=True)
        if str(self.user_id) in dados["usuarios"]:
            dados["usuarios"][str(self.user_id)]["farms"] = []
            dados["usuarios"][str(self.user_id)]["pagamentos"] = []
            dados["usuarios"][str(self.user_id)]["dinheiro_sujo"] = 0.0
            dados["usuarios"][str(self.user_id)]["transacoes_dinheiro_sujo"] = []
            dados["usuarios"][str(self.user_id)]["vendas_drogas"] = []
            salvar_dados()
        await interaction.followup.send("✅ Semana resetada com sucesso!", ephemeral=True)
        await log_admin("RESET SEMANAL", f"Usuário: {self.user_name}\nAdmin: {interaction.user.mention}", 0xffa500)
        await atualizar_ranking()

    @discord.ui.button(label="Cancelar", style=discord.ButtonStyle.secondary, emoji="❌")
    async def cancel(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_message("Reset cancelado.", ephemeral=True)


class ConfirmarFechamentoView(View):
    def __init__(self, user_id, canal):
        super().__init__(timeout=60)
        self.user_id = user_id
        self.canal = canal

    @discord.ui.button(label="Sim, fechar", style=discord.ButtonStyle.danger, emoji="✅")
    async def confirmar(self, interaction: discord.Interaction, button: Button):
        if not is_admin(interaction.user):
            await interaction.response.send_message("Apenas administradores!", ephemeral=True)
            return
        await interaction.response.defer(ephemeral=True, thinking=True)
        if str(self.user_id) in dados["canais"]:
            del dados["canais"][str(self.user_id)]
            salvar_dados()
        await self.canal.delete()
        await interaction.followup.send("Canal fechado!", ephemeral=True)
        await log_acao("fechar_canal", interaction.user, f"Canal {self.canal.name} fechado", 0xff0000)

    @discord.ui.button(label="Cancelar", style=discord.ButtonStyle.secondary, emoji="❌")
    async def cancelar(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_message("Cancelado!", ephemeral=True)


class MudarNomeModal(Modal, title="Mudar Nome do Canal"):
    novo_nome = TextInput(label="Novo nome", placeholder="Ex: farm-lucas", required=True, max_length=90)

    def __init__(self, canal):
        super().__init__()
        self.canal = canal

    async def on_submit(self, interaction: discord.Interaction):
        if not is_admin(interaction.user):
            await interaction.response.send_message("Apenas administradores!", ephemeral=True)
            return
        await interaction.response.defer(ephemeral=True, thinking=True)
        nome = ''.join(c for c in self.novo_nome.value.lower().replace(" ", "-") if c.isalnum() or c == '-') or "farm"
        try:
            await self.canal.edit(name=nome)
            await interaction.followup.send(f"Nome alterado para {nome}", ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"Erro: {str(e)[:100]}", ephemeral=True)


# ========= BACKUP =========
class BackupView(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Criar Backup", style=discord.ButtonStyle.success, emoji="💾")
    async def criar_backup(self, interaction: discord.Interaction, button: Button):
        if not is_admin(interaction.user):
            await interaction.response.send_message("Sem permissão!", ephemeral=True)
            return
        await interaction.response.defer(ephemeral=True, thinking=True)
        backup_nome = await salvar_backup_completo(interaction.user.name)
        await interaction.followup.send(f"✅ Backup **{backup_nome}** criado!", ephemeral=True)
        await log_admin("BACKUP CRIADO", f"Admin: {interaction.user.mention}\nArquivo: {backup_nome}", 0x00ff00)

    @discord.ui.button(label="Apagar Backups Locais", style=discord.ButtonStyle.danger, emoji="🗑️")
    async def apagar_backups(self, interaction: discord.Interaction, button: Button):
        if not is_admin(interaction.user):
            await interaction.response.send_message("Sem permissão!", ephemeral=True)
            return
        await interaction.response.defer(ephemeral=True, thinking=True)
        backups = [a for a in os.listdir('.') if a.startswith('backup_') and a.endswith('.json')]
        if not backups:
            await interaction.followup.send("Nenhum backup local encontrado.", ephemeral=True)
            return
        for b in backups:
            os.remove(b)
        await interaction.followup.send(f"{len(backups)} backup(s) locais deletados!", ephemeral=True)
        await log_admin("BACKUPS DELETADOS", f"Admin: {interaction.user.mention}\nQtd: {len(backups)}", 0xff0000)

    @discord.ui.button(label="Recarregar Backup", style=discord.ButtonStyle.primary, emoji="🔄")
    async def recarregar_backup(self, interaction: discord.Interaction, button: Button):
        if not is_admin(interaction.user):
            await interaction.response.send_message("Sem permissão!", ephemeral=True)
            return
        await interaction.response.defer(ephemeral=True, thinking=True)
        backups = sorted(glob.glob("backup_completo_*.json"), reverse=True)
        if not backups:
            await interaction.followup.send("Nenhum backup encontrado para recarregar.", ephemeral=True)
            return
        view = RecarregarBackupSelectView(backups)
        await interaction.followup.send("Selecione o backup que deseja restaurar:", view=view, ephemeral=True)


class RecarregarBackupSelectView(View):
    def __init__(self, backups):
        super().__init__(timeout=120)
        self.backups = backups
        options = []
        for b in backups[:25]:
            try:
                with open(b, "r", encoding="utf-8") as f:
                    data = json.load(f)
                info = f"{data.get('data_backup', '?')} - {data.get('admin', '?')}"
            except:
                info = b
            options.append(discord.SelectOption(label=info[:100], value=b))
        if options:
            self.add_item(BackupSelectDropdown(options))


class BackupSelectDropdown(Select):
    def __init__(self, options):
        super().__init__(placeholder="Escolha um backup para restaurar...", options=options)

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True, thinking=True)
        arquivo = self.values[0]
        try:
            with open(arquivo, "r", encoding="utf-8") as f:
                backup_data = json.load(f)
            if "dados" in backup_data:
                dados.clear()
                dados.update(backup_data["dados"])
                salvar_dados()
            await interaction.followup.send(f"✅ Backup restaurado!\n**Arquivo:** {arquivo}\n**Data:** {backup_data.get('data_backup', '?')}", ephemeral=True)
            await log_admin("BACKUP RESTAURADO", f"Admin: {interaction.user.mention}\nArquivo: {arquivo}", 0x00ff00)
            await atualizar_ranking()
        except Exception as e:
            await interaction.followup.send(f"Erro ao recarregar backup: {e}", ephemeral=True)


# ========= BOTÃO CRIAR CANAL =========
class BotaoCriarCanalView(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Criar Meu Canal Privado", style=discord.ButtonStyle.success, emoji="🔓")
    async def criar_canal(self, interaction: discord.Interaction, button: Button):
        await interaction.response.defer(ephemeral=True, thinking=True)
        if interaction.guild is None:
            await interaction.followup.send("Use em um servidor!", ephemeral=True)
            return
        if not interaction.guild.me.guild_permissions.manage_channels:
            await interaction.followup.send("Bot precisa de permissão de Administrador.", ephemeral=True)
            return
        if str(interaction.user.id) in dados["canais"]:
            canal = interaction.guild.get_channel(dados["canais"][str(interaction.user.id)])
            if canal:
                await interaction.followup.send(f"Você já possui um canal! Acesse: {canal.mention}", ephemeral=True)
                return
            else:
                del dados["canais"][str(interaction.user.id)]
                salvar_dados()
        try:
            categoria = interaction.guild.get_channel(CATEGORIA_FARMS_ID)
            if not categoria:
                await interaction.followup.send("Categoria não encontrada!", ephemeral=True)
                return
            overwrites = {
                interaction.guild.default_role: discord.PermissionOverwrite(read_messages=False),
                interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True, attach_files=True, embed_links=True, add_reactions=True, read_message_history=True),
                interaction.guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True, manage_channels=True, attach_files=True, embed_links=True, read_message_history=True)
            }
            for cargo_id in CARGOS_ADMIN_IDS:
                cargo = interaction.guild.get_role(cargo_id)
                if cargo:
                    overwrites[cargo] = discord.PermissionOverwrite(read_messages=True, send_messages=True, attach_files=True, embed_links=True, manage_channels=True)
            nome = f"farm-{interaction.user.name}".lower().replace(" ", "-")[:90]
            canal = await categoria.create_text_channel(nome, overwrites=overwrites)
            dados["canais"][str(interaction.user.id)] = canal.id
            salvar_dados()
            view = FarmChannelView(interaction.user.id, interaction.user.name, canal.id)
            embed = discord.Embed(
                title="SEU CANAL PRIVADO",
                description=f"Bem-vindo(a) {interaction.user.mention}!\n\n🔒 Apenas você e administradores têm acesso.\n\n**BOTÕES DISPONÍVEIS:**\n📦 **Farm Produtos** - Registrar farm\n💰 **Farm Dinheiro Sujo** - Registrar C4/dinheiro sujo\n💊 **Venda de Drogas** - Registrar vendas\n✏️ **Editar Registro** - Corrigir um registro\n📋 **Meus Registros** - Ver histórico\n\n**BOTÕES ADMIN:**\n📊 **Fechar Caixa** - Fechar caixa semanal\n✏️ **Mudar Nome** - Renomear canal\n📜 **Histórico Caixa** - Ver fechamentos\n🔄 **Reset Semanal** - Limpar dados\n🗑️ **Fechar Canal** - Deletar canal",
                color=discord.Color.green()
            )
            await canal.send(embed=embed, view=view)
            await log_acao("criar_canal", interaction.user, f"Canal criado: {canal.mention}", 0x00ff00)
            await interaction.followup.send(f"✅ Canal criado! Acesse: {canal.mention}", ephemeral=True)
            await atualizar_ranking()
        except Exception as e:
            await interaction.followup.send(f"Erro: {str(e)[:200]}", ephemeral=True)


# ========= PAINEL DE SET =========
class SetPainelView(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Solicitar SET", style=discord.ButtonStyle.success, emoji="📋")
    async def solicitar_set(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_modal(SolicitarSetModal())


class SolicitarSetModal(Modal, title="Solicitar SET"):
    nome = TextInput(label="Nome", placeholder="Seu nome no jogo", required=True)
    id_jogo = TextInput(label="ID do Jogo", placeholder="Ex: 123456", required=True)

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True, thinking=True)
        sol_id = str(int(datetime.now().timestamp()))
        dados["solicitacoes_set"][sol_id] = {
            "user_id": interaction.user.id,
            "user_name": interaction.user.name,
            "nome": self.nome.value.strip(),
            "id_jogo": self.id_jogo.value.strip(),
            "data": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "status": "pendente"
        }
        salvar_dados()
        embed = discord.Embed(
            title="📋 NOVA SOLICITAÇÃO DE SET",
            description=f"**Discord:** {interaction.user.mention}\n**Nome no jogo:** {self.nome.value}\n**ID do Jogo:** {self.id_jogo.value}",
            color=discord.Color.yellow(),
            timestamp=datetime.now()
        )
        embed.set_footer(text=f"ID da solicitação: {sol_id}")
        canal_conf = bot.get_channel(CANAL_SET_CONFIRMACAO_ID)
        if canal_conf:
            view = AceitarRecusarSetView(sol_id, interaction.user.id)
            await canal_conf.send(embed=embed, view=view)
        await interaction.followup.send("✅ Sua solicitação foi enviada! Aguarde a aprovação de um administrador.", ephemeral=True)
        await log_admin("NOVA SOLICITAÇÃO DE SET", f"Usuário: {interaction.user.mention}\nNome: {self.nome.value}\nID: {self.id_jogo.value}", 0xffd700)


class AceitarRecusarSetView(View):
    def __init__(self, sol_id, user_id):
        super().__init__(timeout=None)
        self.sol_id = sol_id
        self.user_id = user_id

    @discord.ui.button(label="Aceitar", style=discord.ButtonStyle.success, emoji="✅")
    async def aceitar(self, interaction: discord.Interaction, button: Button):
        if not is_admin(interaction.user):
            await interaction.response.send_message("Apenas administradores podem aceitar solicitações.", ephemeral=True)
            return
        view = EscolherCargoSetView(self.sol_id, self.user_id, interaction.message)
        await interaction.response.send_message("Escolha o cargo para atribuir:", view=view, ephemeral=True)

    @discord.ui.button(label="Recusar", style=discord.ButtonStyle.danger, emoji="❌")
    async def recusar(self, interaction: discord.Interaction, button: Button):
        if not is_admin(interaction.user):
            await interaction.response.send_message("Apenas administradores podem recusar solicitações.", ephemeral=True)
            return
        await interaction.response.defer(ephemeral=True, thinking=True)
        sol = dados["solicitacoes_set"].get(self.sol_id)
        if sol:
            sol["status"] = "recusado"
            sol["admin_id"] = interaction.user.id
            salvar_dados()
        try:
            embed = interaction.message.embeds[0]
            embed.color = discord.Color.red()
            embed.title = "❌ SOLICITAÇÃO DE SET RECUSADA"
            embed.add_field(name="Recusado por", value=interaction.user.mention, inline=False)
            await interaction.message.edit(embed=embed, view=None)
        except:
            pass
        try:
            user = await bot.fetch_user(self.user_id)
            await user.send(embed=discord.Embed(
                title="❌ Sua solicitação de SET foi recusada",
                description=f"Um administrador recusou sua solicitação. Entre em contato com a liderança para mais informações.",
                color=discord.Color.red()
            ))
        except:
            pass
        await interaction.followup.send("Solicitação recusada.", ephemeral=True)
        await log_admin("SET RECUSADO", f"Usuário: <@{self.user_id}>\nAdmin: {interaction.user.mention}", 0xff0000)


class EscolherCargoSetView(View):
    def __init__(self, sol_id, user_id, message):
        super().__init__(timeout=120)
        self.sol_id = sol_id
        self.user_id = user_id
        self.message = message
        self.add_item(CargoSetSelect(sol_id, user_id, message))


class CargoSetSelect(Select):
    def __init__(self, sol_id, user_id, message):
        self.sol_id = sol_id
        self.user_id = user_id
        self.message = message
        options = [discord.SelectOption(label=c["nome"], value=str(c["id"])) for c in CARGOS_SET]
        super().__init__(placeholder="Escolha o cargo para atribuir...", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True, thinking=True)
        cargo_id = int(self.values[0])
        cargo_nome = next((c["nome"] for c in CARGOS_SET if c["id"] == cargo_id), "Desconhecido")
        guild = interaction.guild
        member = guild.get_member(self.user_id)
        if not member:
            try:
                member = await guild.fetch_member(self.user_id)
            except:
                member = None
        if not member:
            await interaction.followup.send("Usuário não encontrado no servidor.", ephemeral=True)
            return
        cargo = guild.get_role(cargo_id)
        if not cargo:
            await interaction.followup.send("Cargo não encontrado.", ephemeral=True)
            return
        try:
            await member.add_roles(cargo, reason=f"SET aprovado por {interaction.user.name}")
        except discord.Forbidden:
            await interaction.followup.send(
                f"❌ Sem permissão para dar o cargo **{cargo_nome}**. "
                f"Verifique se o cargo do bot está **acima** desse cargo na lista de cargos do servidor.",
                ephemeral=True
            )
            return
        except Exception as e:
            await interaction.followup.send(f"Erro ao atribuir cargo: {e}", ephemeral=True)
            return
        sol = dados["solicitacoes_set"].get(self.sol_id)
        if sol:
            sol["status"] = "aceito"
            sol["cargo_dado"] = cargo_id
            sol["admin_id"] = interaction.user.id
            salvar_dados()
        try:
            embed = self.message.embeds[0]
            embed.color = discord.Color.green()
            embed.title = "✅ SOLICITAÇÃO DE SET ACEITA"
            embed.add_field(name="Cargo Atribuído", value=cargo_nome, inline=False)
            embed.add_field(name="Aceito por", value=interaction.user.mention, inline=False)
            await self.message.edit(embed=embed, view=None)
        except:
            pass
        try:
            await member.send(embed=discord.Embed(
                title="✅ Sua solicitação de SET foi aceita!",
                description=f"Você recebeu o cargo **{cargo_nome}**! Bem-vindo(a)!",
                color=discord.Color.green()
            ))
        except:
            pass
        await interaction.followup.send(f"✅ Cargo **{cargo_nome}** atribuído para {member.mention}!", ephemeral=True)
        await log_admin("SET ACEITO", f"Usuário: {member.mention}\nCargo: {cargo_nome}\nAdmin: {interaction.user.mention}", 0x00ff00)


# ========= SISTEMA DE LIVES =========
def extract_platform_from_url(url: str):
    url = url.strip().lower()
    if "twitch.tv" in url:
        match = re.search(r"twitch\.tv/([a-zA-Z0-9_]+)", url)
        if match:
            return ("twitch", match.group(1))
    elif "youtube.com" in url or "youtu.be" in url:
        if "youtube.com/@" in url:
            return ("youtube", url.split("@")[-1].split("/")[0])
        elif "youtube.com/channel/" in url:
            return ("youtube", url.split("/channel/")[-1].split("?")[0])
        elif "youtube.com/c/" in url:
            return ("youtube", url.split("/c/")[-1].split("/")[0])
    elif "kick.com" in url:
        match = re.search(r"kick\.com/([a-zA-Z0-9_]+)", url)
        if match:
            return ("kick", match.group(1))
    elif "tiktok.com" in url:
        match = re.search(r"tiktok\.com/@([a-zA-Z0-9_.]+)", url)
        if match:
            return ("tiktok", match.group(1))
    return (None, None)


twitch_token = None
twitch_token_expiry = 0


async def get_twitch_token():
    global twitch_token, twitch_token_expiry
    if twitch_token and datetime.utcnow().timestamp() < twitch_token_expiry:
        return twitch_token
    if not TWITCH_CLIENT_ID or not TWITCH_CLIENT_SECRET:
        return None
    async with aiohttp.ClientSession() as session:
        async with session.post(
            "https://id.twitch.tv/oauth2/token",
            params={"client_id": TWITCH_CLIENT_ID, "client_secret": TWITCH_CLIENT_SECRET, "grant_type": "client_credentials"}
        ) as resp:
            if resp.status == 200:
                data = await resp.json()
                twitch_token = data["access_token"]
                twitch_token_expiry = datetime.utcnow().timestamp() + data["expires_in"] - 60
                return twitch_token
    return None


async def check_twitch_lives(streamers):
    token = await get_twitch_token()
    if not token:
        return {}
    usernames = [s for s in streamers if s]
    if not usernames:
        return {}
    headers = {"Client-ID": TWITCH_CLIENT_ID, "Authorization": f"Bearer {token}"}
    url = "https://api.twitch.tv/helix/streams?user_login=" + "&user_login=".join(usernames)
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers) as resp:
            if resp.status == 200:
                data = await resp.json()
                return {s["user_login"].lower(): s for s in data.get("data", [])}
    return {}


async def check_youtube_lives(streamers):
    if not YOUTUBE_API_KEY:
        return {}
    live_data = {}
    for ch_id in streamers:
        if not ch_id:
            continue
        url = f"https://www.googleapis.com/youtube/v3/search?part=snippet&channelId={ch_id}&eventType=live&type=video&key={YOUTUBE_API_KEY}"
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    for item in data.get("items", []):
                        live_data[ch_id] = item
    return live_data


async def check_tiktok_live(username):
    try:
        headers = {"User-Agent": "Mozilla/5.0", "Accept-Language": "en-US,en;q=0.9", "Accept": "text/html", "Referer": "https://www.tiktok.com/"}
        async with aiohttp.ClientSession() as session:
            url = f"https://www.tiktok.com/@{username}/live"
            async with session.get(url, headers=headers, allow_redirects=True) as resp:
                if resp.status != 200:
                    return None
                html = await resp.text()
                title_match = re.search(r'"title":"(.*?)"', html)
                if not title_match:
                    return None
                title = title_match.group(1).replace('\\u002F', '/').replace('\\u0026', '&')
                thumb_match = re.search(r'"thumbnail_url":"(.*?)"', html)
                thumbnail = thumb_match.group(1).replace('\\u002F', '/') if thumb_match else None
                return {"title": title, "thumbnail": thumbnail, "url": url}
    except:
        return None


async def check_tiktok_lives(streamers):
    live_data = {}
    for username in streamers:
        if not username:
            continue
        info = await check_tiktok_live(username)
        if info:
            live_data[username] = info
    return live_data


@tasks.loop(minutes=1)
async def live_check_loop():
    for server_id_str in dados["lives"]["config"]:
        config = dados["lives"]["config"][server_id_str]
        guild = bot.get_guild(int(server_id_str))
        if not guild:
            continue
        plataformas = config.get("platforms", {"twitch": True, "youtube": True, "kick": True, "tiktok": True})
        canal_id = config.get("channel")
        canal = bot.get_channel(canal_id) if canal_id else None
        role_id = config.get("role")
        role_mention = f"<@&{role_id}>" if role_id else ""
        streamers_dict = dados["lives"]["streamers"].get(server_id_str, {})
        status_server = dados["lives"]["status"].setdefault(server_id_str, {})

        if plataformas.get("twitch"):
            twitch_users = [data.get("twitch") for data in streamers_dict.values() if data.get("twitch")]
            lives = await check_twitch_lives(twitch_users)
            for uid, data in streamers_dict.items():
                twitch_name = data.get("twitch")
                status_server.setdefault(uid, {})["twitch"] = twitch_name.lower() in lives if twitch_name else False
                if twitch_name and twitch_name.lower() in lives:
                    last_key = f"twitch_{uid}"
                    live_info = lives[twitch_name.lower()]
                    last = dados["lives"]["last_notified"].get(last_key)
                    if last != live_info["id"]:
                        dados["lives"]["last_notified"][last_key] = live_info["id"]
                        nome_streamer = data.get("nome", twitch_name)
                        observacao = data.get("observacao", "")
                        if canal:
                            desc = f"**{nome_streamer}** está ao vivo!"
                            if observacao:
                                desc += f"\n{observacao}"
                            embed = discord.Embed(title="🔴 LIVE NA TWITCH", description=desc, color=0x9146ff)
                            embed.add_field(name="Título", value=live_info['title'], inline=False)
                            embed.add_field(name="Link", value=f"https://twitch.tv/{twitch_name}", inline=False)
                            if 'thumbnail_url' in live_info:
                                thumb_url = live_info['thumbnail_url'].replace('{width}', '640').replace('{height}', '360')
                                embed.set_image(url=thumb_url)
                            await canal.send(content=role_mention, embed=embed)

        if plataformas.get("youtube"):
            yt_users = [data.get("youtube") for data in streamers_dict.values() if data.get("youtube")]
            lives = await check_youtube_lives(yt_users)
            for uid, data in streamers_dict.items():
                yt_ch = data.get("youtube")
                status_server.setdefault(uid, {})["youtube"] = yt_ch in lives if yt_ch else False
                if yt_ch and yt_ch in lives:
                    last_key = f"yt_{uid}"
                    video = lives[yt_ch]
                    video_id = video["id"]["videoId"]
                    last = dados["lives"]["last_notified"].get(last_key)
                    if last != video_id:
                        dados["lives"]["last_notified"][last_key] = video_id
                        nome_streamer = data.get("nome", yt_ch)
                        observacao = data.get("observacao", "")
                        if canal:
                            desc = f"**{nome_streamer}** está ao vivo!"
                            if observacao:
                                desc += f"\n{observacao}"
                            embed = discord.Embed(title="🔴 LIVE NO YOUTUBE", description=desc, color=0xff0000)
                            embed.add_field(name="Título", value=video['snippet']['title'], inline=False)
                            embed.add_field(name="Link", value=f"https://youtube.com/watch?v={video_id}", inline=False)
                            await canal.send(content=role_mention, embed=embed)

        if plataformas.get("tiktok"):
            tiktok_users = [data.get("tiktok") for data in streamers_dict.values() if data.get("tiktok")]
            lives = await check_tiktok_lives(tiktok_users)
            for uid, data in streamers_dict.items():
                tiktok_name = data.get("tiktok")
                status_server.setdefault(uid, {})["tiktok"] = tiktok_name in lives if tiktok_name else False
                if tiktok_name and tiktok_name in lives:
                    last_key = f"tiktok_{uid}"
                    live_info = lives[tiktok_name]
                    last = dados["lives"]["last_notified"].get(last_key)
                    if last != live_info.get("url"):
                        dados["lives"]["last_notified"][last_key] = live_info.get("url")
                        nome_streamer = data.get("nome", tiktok_name)
                        observacao = data.get("observacao", "")
                        if canal:
                            desc = f"Fala galera, **{nome_streamer}** acabou de entrar ao vivo na **Tiktok!** Vem colar com a gente!"
                            embed = discord.Embed(title="🔴 LIVE NO TIKTOK", description=desc, color=0xff0050, url=live_info.get("url"))
                            embed.add_field(name="Título", value=live_info.get("title", "Live"), inline=False)
                            embed.set_footer(text="TIKTOK • Hoje às " + datetime.now().strftime("%H:%M"))
                            if live_info.get("thumbnail"):
                                embed.set_image(url=live_info["thumbnail"])
                            view = View(timeout=None)
                            view.add_item(Button(label="Assistir Agora", style=discord.ButtonStyle.link, url=live_info.get("url")))
                            await canal.send(content=role_mention, embed=embed, view=view)

        for uid, data in streamers_dict.items():
            if data.get("kick"):
                status_server.setdefault(uid, {})["kick"] = False

    salvar_dados()
    for server_id_str in dados["lives"]["config"]:
        canal_painel = bot.get_channel(CANAL_LIVES_PAINEL_ID)
        if canal_painel:
            view = LiveConfigView(int(server_id_str))
            embed = await view.build_embed()
            async for msg in canal_painel.history(limit=5):
                if msg.author == bot.user and msg.embeds:
                    await msg.edit(embed=embed)
                    break


@live_check_loop.before_loop
async def before_live_check():
    await bot.wait_until_ready()


class LiveConfigView(View):
    def __init__(self, server_id):
        super().__init__(timeout=None)
        self.server_id = server_id

    async def get_config(self):
        return dados["lives"]["config"].setdefault(str(self.server_id), {"channel": None, "role": None, "platforms": {"twitch": True, "youtube": True, "kick": True, "tiktok": True}})

    async def build_embed(self):
        config = await self.get_config()
        canal_info = f"<#{config['channel']}>" if config['channel'] else "Não definido"
        cargo_info = f"<@&{config['role']}>" if config['role'] else "Não definido"
        plats = config['platforms']
        embed = discord.Embed(title="🔔 NOTIFICAÇÃO DE LIVES", color=0x9b59b6)
        embed.add_field(name="Canal", value=canal_info, inline=False)
        embed.add_field(name="Cargo (ping)", value=cargo_info, inline=False)
        status = "\n".join([
            f"Twitch: {'✅ Ativado' if plats['twitch'] else '❌ Desativado'}",
            f"YouTube: {'✅ Ativado' if plats['youtube'] else '❌ Desativado'}",
            f"Kick: {'✅ Ativado' if plats['kick'] else '❌ Desativado'}",
            f"TikTok: {'✅ Ativado' if plats['tiktok'] else '❌ Desativado'}"
        ])
        embed.add_field(name="Plataformas Monitoradas", value=status, inline=False)
        streamers = dados["lives"]["streamers"].get(str(self.server_id), {})
        if streamers:
            lista_streamers = ""
            for uid, data in streamers.items():
                nome = data.get("nome", uid)
                plats_list = []
                for p in ["twitch", "youtube", "kick", "tiktok"]:
                    if data.get(p):
                        online = dados["lives"]["status"].get(str(self.server_id), {}).get(uid, {}).get(p, False)
                        emoji = "🟢" if online else "🔴"
                        plats_list.append(f"{emoji} {p.capitalize()}: {data[p]}")
                if plats_list:
                    lista_streamers += f"**<@{uid}>**\n" + "\n".join(plats_list) + "\n\n"
            if lista_streamers:
                embed.add_field(name="📋 Streamers Cadastrados", value=lista_streamers[:1024], inline=False)
        return embed

    @discord.ui.button(label="Definir Canal", style=discord.ButtonStyle.primary, emoji="📝")
    async def set_channel(self, interaction: discord.Interaction, button: Button):
        if not is_admin(interaction.user):
            await interaction.response.send_message("Sem permissão.", ephemeral=True)
            return
        modal = SetCanalModal(self.server_id, self)
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="Configuração", style=discord.ButtonStyle.secondary, emoji="⚙️")
    async def configuracao(self, interaction: discord.Interaction, button: Button):
        if not is_admin(interaction.user):
            await interaction.response.send_message("Sem permissão.", ephemeral=True)
            return
        await interaction.response.defer()
        view = ConfigSteamersView(self.server_id, self)
        embed = discord.Embed(title="⚙️ CONFIGURAÇÃO DE STREAMERS", description="Gerencie os streamers e plataformas.", color=0x7289da)
        await interaction.followup.send(embed=embed, view=view, ephemeral=True)

    @discord.ui.button(label="Adicionar Streamer", style=discord.ButtonStyle.success, emoji="➕", row=1)
    async def adicionar(self, interaction: discord.Interaction, button: Button):
        if not (is_admin(interaction.user) or is_membro(interaction.user)):
            await interaction.response.send_message("Você não tem permissão para adicionar streamer.", ephemeral=True)
            return
        await interaction.response.send_modal(AddStreamerByLinkModal(self.server_id, self))

    @discord.ui.button(label="Atualizar Painel", style=discord.ButtonStyle.secondary, emoji="🔄", row=1)
    async def atualizar_painel(self, interaction: discord.Interaction, button: Button):
        if not is_admin(interaction.user):
            await interaction.response.send_message("Sem permissão.", ephemeral=True)
            return
        await interaction.response.defer()
        embed = await self.build_embed()
        await interaction.message.edit(embed=embed, view=self)


class SetCanalModal(Modal, title="Definir Canal e Cargo"):
    canal_id = TextInput(label="ID do canal de notícias", required=True)
    cargo_id = TextInput(label="ID do cargo para mencionar", required=True)

    def __init__(self, server_id, parent_view):
        super().__init__()
        self.server_id = server_id
        self.parent_view = parent_view

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True, thinking=True)
        try:
            cid = int(self.canal_id.value.strip())
            rid = int(self.cargo_id.value.strip())
            config = dados["lives"]["config"].setdefault(str(self.server_id), {"platforms": {"twitch": True, "youtube": True, "kick": True, "tiktok": True}})
            config["channel"] = cid
            config["role"] = rid
            salvar_dados()
            embed = await self.parent_view.build_embed()
            await interaction.message.edit(embed=embed, view=self.parent_view)
            await interaction.followup.send("✅ Canal e cargo definidos!", ephemeral=True)
        except:
            await interaction.followup.send("IDs inválidos.", ephemeral=True)


class ConfigSteamersView(View):
    def __init__(self, server_id, parent_view):
        super().__init__(timeout=None)
        self.server_id = server_id
        self.parent_view = parent_view

    @discord.ui.button(label="Adicionar Streamer", style=discord.ButtonStyle.success, emoji="➕")
    async def add(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_modal(AddStreamerByLinkModal(self.server_id, self.parent_view))

    @discord.ui.button(label="Remover Streamer", style=discord.ButtonStyle.danger, emoji="🗑️")
    async def remove(self, interaction: discord.Interaction, button: Button):
        await interaction.response.defer(ephemeral=True)
        streamers = dados["lives"]["streamers"].get(str(self.server_id), {})
        if not streamers:
            await interaction.followup.send("Nenhum streamer cadastrado.", ephemeral=True)
            return
        view = RemoveStreamerSelectView(self.server_id, self.parent_view)
        await interaction.followup.send("Selecione o streamer para remover:", view=view, ephemeral=True)

    @discord.ui.button(label="Twitch", style=discord.ButtonStyle.primary, emoji="📺", row=1)
    async def toggle_twitch(self, interaction: discord.Interaction, button: Button):
        await interaction.response.defer(ephemeral=True)
        config = dados["lives"]["config"].setdefault(str(self.server_id), {"platforms": {"twitch": True}})
        config["platforms"]["twitch"] = not config["platforms"].get("twitch", True)
        salvar_dados()
        await interaction.followup.send(f"Twitch {'ativado' if config['platforms']['twitch'] else 'desativado'}.", ephemeral=True)

    @discord.ui.button(label="YouTube", style=discord.ButtonStyle.danger, emoji="▶️", row=1)
    async def toggle_youtube(self, interaction: discord.Interaction, button: Button):
        await interaction.response.defer(ephemeral=True)
        config = dados["lives"]["config"].setdefault(str(self.server_id), {"platforms": {"youtube": True}})
        config["platforms"]["youtube"] = not config["platforms"].get("youtube", True)
        salvar_dados()
        await interaction.followup.send(f"YouTube {'ativado' if config['platforms']['youtube'] else 'desativado'}.", ephemeral=True)

    @discord.ui.button(label="Kick", style=discord.ButtonStyle.success, emoji="🟢", row=1)
    async def toggle_kick(self, interaction: discord.Interaction, button: Button):
        await interaction.response.defer(ephemeral=True)
        config = dados["lives"]["config"].setdefault(str(self.server_id), {"platforms": {"kick": True}})
        config["platforms"]["kick"] = not config["platforms"].get("kick", True)
        salvar_dados()
        await interaction.followup.send(f"Kick {'ativado' if config['platforms']['kick'] else 'desativado'}.", ephemeral=True)

    @discord.ui.button(label="TikTok", style=discord.ButtonStyle.secondary, emoji="🎵", row=1)
    async def toggle_tiktok(self, interaction: discord.Interaction, button: Button):
        await interaction.response.defer(ephemeral=True)
        config = dados["lives"]["config"].setdefault(str(self.server_id), {"platforms": {"tiktok": True}})
        config["platforms"]["tiktok"] = not config["platforms"].get("tiktok", True)
        salvar_dados()
        await interaction.followup.send(f"TikTok {'ativado' if config['platforms']['tiktok'] else 'desativado'}.", ephemeral=True)


class RemoveStreamerSelectView(View):
    def __init__(self, server_id, parent_view):
        super().__init__(timeout=120)
        self.server_id = server_id
        self.parent_view = parent_view
        streamers = dados["lives"]["streamers"].get(str(server_id), {})
        options = []
        for uid, data in streamers.items():
            nome = data.get("nome", uid)
            plats = []
            for p in ["twitch", "youtube", "kick", "tiktok"]:
                if data.get(p):
                    plats.append(p.capitalize())
            desc = f"{nome} ({', '.join(plats)})" if plats else nome
            options.append(discord.SelectOption(label=desc[:100], value=uid))
        if options:
            self.add_item(StreamerRemoveDropdown(options, server_id, parent_view))


class StreamerRemoveDropdown(Select):
    def __init__(self, options, server_id, parent_view):
        super().__init__(placeholder="Escolha um streamer para remover...", options=options)
        self.server_id = server_id
        self.parent_view = parent_view

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        uid = self.values[0]
        if str(self.server_id) in dados["lives"]["streamers"] and uid in dados["lives"]["streamers"][str(self.server_id)]:
            nome = dados["lives"]["streamers"][str(self.server_id)][uid].get("nome", uid)
            del dados["lives"]["streamers"][str(self.server_id)][uid]
            salvar_dados()
            await interaction.followup.send(f"Streamer **{nome}** removido!", ephemeral=True)
            try:
                embed = await self.parent_view.build_embed()
                await interaction.message.edit(embed=embed, view=self.parent_view)
            except:
                pass
        else:
            await interaction.followup.send("Streamer não encontrado.", ephemeral=True)


class AddStreamerByLinkModal(Modal, title="Adicionar Streamer"):
    plataforma   = TextInput(label="PLATAFORMA (twitch/youtube/kick/tiktok)", placeholder="Ex: twitch", required=True)
    username     = TextInput(label="USERNAME DO STREAMER", placeholder="Ex: alanzoka", required=True)
    discord_user = TextInput(label="DISCORD DO STREAMER (opcional)", placeholder="ID ou @ do usuário", required=False)
    observacao   = TextInput(label="OBSERVAÇÃO (mensagem padrão)", placeholder="Aparecerá na notificação da live", required=False)

    def __init__(self, server_id, parent_view):
        super().__init__()
        self.server_id = server_id
        self.parent_view = parent_view

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True, thinking=True)
        plat_input = self.plataforma.value.strip().lower()
        username_input = self.username.value.strip()
        obs = self.observacao.value.strip()
        extracted_plat, extracted_id = extract_platform_from_url(username_input)
        if extracted_plat and extracted_id:
            platform = extracted_plat
            identifier = extracted_id
            nome_streamer = identifier
        else:
            if plat_input not in ["twitch", "youtube", "kick", "tiktok"]:
                await interaction.followup.send("Plataforma inválida.", ephemeral=True)
                return
            platform = plat_input
            identifier = username_input
            nome_streamer = identifier
        uid = str(interaction.user.id)
        if self.discord_user.value.strip():
            try:
                uid_str = self.discord_user.value.strip().replace("<@!", "").replace("<@", "").replace(">", "")
                uid = str(int(uid_str))
                member = interaction.guild.get_member(int(uid))
                if member:
                    nome_streamer = member.display_name
            except:
                pass
        if is_membro(interaction.user) and not is_admin(interaction.user):
            if uid != str(interaction.user.id):
                await interaction.followup.send("Você só pode adicionar seu próprio canal.", ephemeral=True)
                return
        if str(self.server_id) not in dados["lives"]["streamers"]:
            dados["lives"]["streamers"][str(self.server_id)] = {}
        if uid not in dados["lives"]["streamers"][str(self.server_id)]:
            dados["lives"]["streamers"][str(self.server_id)][uid] = {"nome": nome_streamer, "twitch": None, "youtube": None, "kick": None, "tiktok": None, "observacao": ""}
        dados["lives"]["streamers"][str(self.server_id)][uid][platform] = identifier
        dados["lives"]["streamers"][str(self.server_id)][uid]["nome"] = nome_streamer
        if obs:
            dados["lives"]["streamers"][str(self.server_id)][uid]["observacao"] = obs
        salvar_dados()
        await interaction.followup.send(f"Streamer **{nome_streamer}** adicionado em **{platform}**!", ephemeral=True)
        try:
            embed = await self.parent_view.build_embed()
            await interaction.message.edit(embed=embed, view=self.parent_view)
        except:
            pass


# ========= PAINEL DE AÇÕES =========
class ActionPanelView(View):
    def __init__(self, server_id):
        super().__init__(timeout=None)
        self.server_id = server_id

    @discord.ui.button(label="Abrir Ação", style=discord.ButtonStyle.success, emoji="⚔️")
    async def open_action(self, interaction: discord.Interaction, button: Button):
        if not pode_registrar_acao(interaction.user):
            await interaction.response.send_message("Você não tem permissão para registrar ações.", ephemeral=True)
            return
        await interaction.response.send_modal(ActionModal(self.server_id))

    @discord.ui.button(label="Pagamento", style=discord.ButtonStyle.primary, emoji="💰")
    async def payment(self, interaction: discord.Interaction, button: Button):
        if not pode_registrar_acao(interaction.user):
            await interaction.response.send_message("Você não tem permissão para gerenciar pagamentos.", ephemeral=True)
            return
        await interaction.response.defer(ephemeral=True, thinking=True)
        server_actions = dados["acoes"].get(str(self.server_id), {})
        unpaid = {k: v for k, v in server_actions.items() if not v.get("pago", False)}
        if not unpaid:
            await interaction.followup.send("Nenhuma ação pendente.", ephemeral=True)
            return
        view = ActionSelectView(self.server_id, unpaid)
        await interaction.followup.send("Selecione a ação:", view=view, ephemeral=True)


class ActionModal(Modal, title="Registrar Ação"):
    nome_acao  = TextInput(label="Ação (nome do lugar)", placeholder="Ex: Assalto ao Banco Central", required=True)
    valor      = TextInput(label="Valor (R$)", placeholder="Ex: 25000", required=True)
    resultado  = TextInput(label="Vitória ou Derrota", placeholder="Digite Vitória ou Derrota", required=True)
    darkcoin   = TextInput(label="Darkcoin", placeholder="Quantidade, 0 se não teve", required=True)
    data_acao  = TextInput(label="Data da Ação (DD/MM/AAAA)", placeholder="Ex: 25/12/2025", required=True)

    def __init__(self, server_id):
        super().__init__()
        self.server_id = server_id

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True, thinking=True)
        try:
            valor_num = float(self.valor.value.replace(",", "."))
        except ValueError:
            await interaction.followup.send("Valor inválido!", ephemeral=True)
            return
        try:
            dark_num = int(self.darkcoin.value)
        except ValueError:
            await interaction.followup.send("Darkcoin inválida!", ephemeral=True)
            return
        result = self.resultado.value.strip().lower()
        if result not in ["vitória", "derrota", "vitoria"]:
            await interaction.followup.send("Resultado inválido.", ephemeral=True)
            return
        result = "Vitória" if result in ["vitória", "vitoria"] else "Derrota"
        data_str = self.data_acao.value.strip()
        try:
            datetime.strptime(data_str, "%d/%m/%Y")
        except ValueError:
            await interaction.followup.send("Data inválida! Use DD/MM/AAAA.", ephemeral=True)
            return
        self.action_info = {
            "nome_acao": self.nome_acao.value.strip(), "valor": valor_num,
            "resultado": result, "darkcoin": dark_num,
            "data_acao": data_str, "puxado_por": interaction.user.id
        }
        view = MemberSelectView(self.server_id, self.action_info)
        await interaction.followup.send("Selecione os membros que participaram da ação:", view=view, ephemeral=True)


class MemberSelectView(View):
    def __init__(self, server_id, action_data):
        super().__init__(timeout=120)
        self.server_id = server_id
        self.action_data = action_data
        self.selected_members = [action_data["puxado_por"]]

    @discord.ui.select(cls=UserSelect, placeholder="Selecione os membros...", min_values=1, max_values=25)
    async def select_members(self, interaction: discord.Interaction, select: UserSelect):
        self.selected_members = list(set([self.action_data["puxado_por"]] + [u.id for u in select.values]))
        await interaction.response.defer()

    @discord.ui.button(label="Confirmar e Enviar Print", style=discord.ButtonStyle.success, emoji="✅")
    async def confirm(self, interaction: discord.Interaction, button: Button):
        await interaction.response.defer(ephemeral=True, thinking=True)
        if not self.selected_members:
            await interaction.followup.send("Selecione pelo menos um membro.", ephemeral=True)
            return
        self.action_data["membros"] = self.selected_members
        print_urls = []
        await interaction.followup.send("Envie quantas prints quiser. Quando terminar, digite `pronto`.", ephemeral=True)
        while True:
            try:
                msg = await bot.wait_for('message', timeout=300.0, check=lambda m: m.author == interaction.user and m.channel == interaction.channel)
                if msg.content.lower() == "pronto":
                    break
                if msg.attachments:
                    for att in msg.attachments:
                        if att.content_type and att.content_type.startswith('image/'):
                            print_urls.append(att.url)
                else:
                    await interaction.followup.send("Envie uma imagem ou digite `pronto`.", ephemeral=True)
            except asyncio.TimeoutError:
                await interaction.followup.send("Tempo esgotado. As prints enviadas até agora serão salvas.", ephemeral=True)
                break
        self.action_data["print_urls"] = print_urls
        self.action_data["pago"] = False
        self.action_data["data_registro"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        action_id = str(int(datetime.now().timestamp()))
        dados["acoes"].setdefault(str(self.server_id), {})[action_id] = self.action_data
        salvar_dados()
        canal_logs = bot.get_channel(CANAL_ACOES_LOGS_ID)
        if canal_logs:
            embed = discord.Embed(title="NOVA AÇÃO REGISTRADA", color=discord.Color.green(), timestamp=datetime.now())
            embed.add_field(name="Ação", value=self.action_data["nome_acao"], inline=True)
            embed.add_field(name="Valor", value=f"R$ {self.action_data['valor']:,.2f}", inline=True)
            embed.add_field(name="Resultado", value=self.action_data["resultado"], inline=True)
            embed.add_field(name="Darkcoin", value=str(self.action_data["darkcoin"]), inline=True)
            embed.add_field(name="Data", value=self.action_data["data_acao"], inline=True)
            embed.add_field(name="Líder", value=f"<@{self.action_data['puxado_por']}>", inline=True)
            membros_str = " ".join(f"<@{m}>" for m in self.selected_members)
            embed.add_field(name="Participantes", value=membros_str, inline=False)
            if print_urls:
                embed.set_image(url=print_urls[0])
            await canal_logs.send(embed=embed)
        await interaction.followup.send("Ação registrada com sucesso!", ephemeral=True)
        self.stop()


class ActionSelectView(View):
    def __init__(self, server_id, actions):
        super().__init__(timeout=120)
        self.server_id = server_id
        self.add_item(ActionDropdown(actions))


class ActionDropdown(Select):
    def __init__(self, actions):
        options = []
        for k, v in actions.items():
            nome = v.get("nome_acao", "Ação")
            valor = v.get("valor", 0)
            data = v.get("data_acao", "s/d")
            label = f"{nome[:40]} (R$ {valor:,.0f}) - {data}"
            options.append(discord.SelectOption(label=label[:100], value=k))
        super().__init__(placeholder="Escolha uma ação...", options=options)

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True, thinking=True)
        action_id = self.values[0]
        action = dados["acoes"].get(str(interaction.guild_id), {}).get(action_id)
        if not action:
            await interaction.followup.send("Ação não encontrada.", ephemeral=True)
            return
        valor = action["valor"]
        n_membros = len(action["membros"])
        # 50% membros, 50% facção
        membros_total = valor * 0.50
        faccao_total = valor * 0.50
        por_membro = membros_total / n_membros if n_membros > 0 else 0
        embed = discord.Embed(title="RESUMO DO PAGAMENTO", color=discord.Color.orange())
        embed.add_field(name="Ação", value=action.get("nome_acao", "?"), inline=False)
        embed.add_field(name="Data", value=action.get("data_acao", "?"), inline=False)
        embed.add_field(name="Valor Total", value=f"R$ {valor:,.2f}", inline=False)
        embed.add_field(name="Facção (50%)", value=f"R$ {faccao_total:,.2f}", inline=True)
        embed.add_field(name="Membros (50%)", value=f"R$ {membros_total:,.2f}", inline=True)
        embed.add_field(name="Dividido por", value=f"{n_membros} membros", inline=True)
        embed.add_field(name="Cada membro recebe", value=f"R$ {por_membro:,.2f}", inline=True)
        view = ConfirmPaymentView(interaction.guild_id, action_id, membros_total, por_membro, action["membros"])
        await interaction.followup.send(embed=embed, view=view, ephemeral=True)


class ConfirmPaymentView(View):
    def __init__(self, server_id, action_id, valor_membros, valor_por_membro, membros):
        super().__init__(timeout=120)
        self.server_id = server_id
        self.action_id = action_id
        self.valor_membros = valor_membros
        self.valor_por_membro = valor_por_membro
        self.membros = membros

    @discord.ui.button(label="Confirmar Pagamento", style=discord.ButtonStyle.success, emoji="✅")
    async def confirm(self, interaction: discord.Interaction, button: Button):
        await interaction.response.defer(ephemeral=True, thinking=True)
        await interaction.followup.send("Envie as **prints dos comprovantes** (quantas quiser). Quando terminar, digite `pronto`.", ephemeral=True)
        print_urls = []
        def check(m):
            return m.author == interaction.user and m.channel == interaction.channel
        while True:
            try:
                msg = await bot.wait_for('message', timeout=300.0, check=check)
                if msg.content.lower() == "pronto":
                    break
                if msg.attachments:
                    for att in msg.attachments:
                        if att.content_type and att.content_type.startswith('image/'):
                            print_urls.append(att.url)
                else:
                    await interaction.followup.send("Envie uma imagem ou digite `pronto`.", ephemeral=True)
            except asyncio.TimeoutError:
                await interaction.followup.send("Tempo esgotado.", ephemeral=True)
                break
        action = dados["acoes"].get(str(self.server_id), {}).get(self.action_id)
        if action:
            action["pago"] = True
            action["pagamento"] = {
                "valor_membros": self.valor_membros,
                "valor_por_membro": self.valor_por_membro,
                "print_urls": print_urls,
                "data_pagamento": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "admin_id": interaction.user.id
            }
            salvar_dados()
            canal_logs = bot.get_channel(CANAL_ACOES_LOGS_ID)
            if canal_logs:
                embed = discord.Embed(title="PAGAMENTO DE AÇÃO", color=discord.Color.green(), timestamp=datetime.now())
                embed.add_field(name="Ação", value=action.get("nome_acao", "?"), inline=True)
                embed.add_field(name="Por Membro (50% dos membros)", value=f"R$ {self.valor_por_membro:,.2f}", inline=True)
                embed.add_field(name="Admin", value=f"<@{interaction.user.id}>", inline=True)
                if print_urls:
                    embed.set_image(url=print_urls[0])
                await canal_logs.send(embed=embed)
            await interaction.followup.send("Pagamento registrado com sucesso!", ephemeral=True)
        else:
            await interaction.followup.send("Ação não encontrada.", ephemeral=True)


# ========= ADMIN EXTRA =========
class RemoverUsuarioModal(Modal, title="Remover Usuário"):
    user_id = TextInput(label="ID do usuário", required=True)

    async def on_submit(self, interaction: discord.Interaction):
        if not is_admin(interaction.user):
            await interaction.response.send_message("Sem permissão!", ephemeral=True)
            return
        await interaction.response.defer(ephemeral=True, thinking=True)
        try:
            uid = int(self.user_id.value.strip())
            user = await interaction.client.fetch_user(uid)
            if str(uid) in dados["usuarios_banidos"]:
                await interaction.followup.send("Usuário já removido!", ephemeral=True)
                return
            total = await limpar_logs_usuario(uid, user.name)
            await interaction.followup.send(f"✅ {user.mention} removido! Mensagens limpas: {total}", ephemeral=True)
            await log_admin("USUÁRIO REMOVIDO", f"{user.mention} por {interaction.user.mention}", 0xff0000)
            await atualizar_ranking()
        except Exception as e:
            await interaction.followup.send(f"Erro: {e}", ephemeral=True)


# ========= EVENTOS =========
@bot.event
async def on_member_remove(member):
    if str(member.id) in dados["usuarios_banidos"]:
        return
    await log_admin("USUÁRIO SAIU", f"{member.mention} saiu. Iniciando limpeza...")
    await limpar_logs_usuario(member.id, member.name)
    if str(member.id) in dados["canais"]:
        canal = member.guild.get_channel(dados["canais"][str(member.id)])
        if canal:
            try:
                await canal.delete(reason=f"Usuário {member.name} saiu")
            except:
                pass
        del dados["canais"][str(member.id)]
        salvar_dados()
    await log_admin("LIMPEZA CONCLUÍDA", f"{member.mention} removido do sistema.")


@bot.event
async def on_ready():
    print(f"Bot {bot.user} online!")
    live_check_loop.start()
    for guild in bot.guilds:
        # ---- COMPRA E VENDA ----
        canal_vendas = bot.get_channel(CHAT_COMPRA_VENDA_ID)
        if canal_vendas and isinstance(canal_vendas, discord.TextChannel):
            async for msg in canal_vendas.history(limit=10):
                if msg.author == bot.user:
                    await msg.delete()
            await canal_vendas.send(
                embed=discord.Embed(
                    title="SISTEMA DE COMPRA E VENDA",
                    description="🔫 **Venda de Arma**\n🛒 **Compra de Produto**",
                    color=discord.Color.blue()
                ),
                view=CompraVendaView()
            )
        else:
            print(f"⚠️ Canal de compra/venda ({CHAT_COMPRA_VENDA_ID}) não encontrado ou não é um TextChannel.")

        # ---- PAINEL CRIAR CANAL ----
        categoria_painel = guild.get_channel(CATEGORIA_PAINEL_ID)
        if categoria_painel:
            canal_criar = discord.utils.get(categoria_painel.channels, name="criar-canal")
            if not canal_criar:
                canal_criar = await categoria_painel.create_text_channel("criar-canal")
            async for msg in canal_criar.history(limit=5):
                if msg.author == bot.user:
                    await msg.delete()
            await canal_criar.send(
                embed=discord.Embed(
                    title="SISTEMA DE FARM",
                    description="Clique no botão abaixo para criar seu canal privado!\n\n🔒 Apenas você e os administradores terão acesso",
                    color=discord.Color.blue()
                ),
                view=BotaoCriarCanalView()
            )

        # ---- PAINEL DE BACKUP ----
        categoria_backup = guild.get_channel(CATEGORIA_BACKUP_ID)
        if categoria_backup:
            canal_backup_painel = discord.utils.get(categoria_backup.channels, name="painel-backup")
            if not canal_backup_painel:
                canal_backup_painel = await categoria_backup.create_text_channel("painel-backup")
            async for msg in canal_backup_painel.history(limit=5):
                if msg.author == bot.user:
                    await msg.delete()
            await canal_backup_painel.send(
                embed=discord.Embed(
                    title="💾 PAINEL DE BACKUP",
                    description="💾 **Criar Backup** - Salva tudo\n🗑️ **Apagar Backups Locais**\n🔄 **Recarregar Backup** - Restaura backup anterior",
                    color=discord.Color.blue()
                ),
                view=BackupView()
            )

        # ---- PAINEL DE AÇÕES ----
        canal_acoes = bot.get_channel(CANAL_ACOES_PAINEL_ID)
        if canal_acoes:
            async for msg in canal_acoes.history(limit=5):
                if msg.author == bot.user:
                    await msg.delete()
            embed = discord.Embed(
                title="⚔️ PAINEL DE AÇÕES",
                description="Gerencie as ações e os pagamentos da facção.",
                color=discord.Color.dark_red()
            )
            embed.add_field(name="Abrir Ação", value="Registre uma nova ação com valor, data, participantes e prints.", inline=False)
            embed.add_field(name="Pagamento", value="Efetue o pagamento das ações pendentes (50% membros / 50% facção).", inline=False)
            view = ActionPanelView(guild.id)
            await canal_acoes.send(embed=embed, view=view)

        # ---- PAINEL DE SET (AUTOMÁTICO) ----
        canal_set = None
        for ch in guild.text_channels:
            if ch.name == "solicitar-set":
                canal_set = ch
                break
        if not canal_set:
            cat_painel = guild.get_channel(CATEGORIA_PAINEL_ID)
            if cat_painel:
                canal_set = await cat_painel.create_text_channel("solicitar-set")
        if canal_set:
            async for msg in canal_set.history(limit=5):
                if msg.author == bot.user:
                    await msg.delete()
            embed_set = discord.Embed(
                title="📋 PAINEL DE SET",
                description="Clique no botão abaixo para solicitar seu SET.\n\nPreencha o formulário com seu **Nome** e **ID do Jogo**.\nUm administrador irá avaliar sua solicitação.",
                color=discord.Color.gold()
            )
            await canal_set.send(embed=embed_set, view=SetPainelView())

        # ---- PAINEL DE LIVES ----
        canal_lives = bot.get_channel(CANAL_LIVES_PAINEL_ID)
        if canal_lives:
            async for msg in canal_lives.history(limit=5):
                if msg.author == bot.user:
                    await msg.delete()
            view = LiveConfigView(guild.id)
            embed = await view.build_embed()
            await canal_lives.send(embed=embed, view=view)

        # ---- BACKUP AUTOMÁTICO ----
        canal_backup_arquivos = bot.get_channel(CANAL_BACKUP_ARQUIVOS_ID)
        if canal_backup_arquivos:
            await salvar_backup_completo("Sistema (Auto)")

    await atualizar_ranking()
    await log_admin("🤖 BOT INICIADO", f"Bot {bot.user.mention} online!", 0x00ff00)


if __name__ == "__main__":
    carregar_dados()
    bot.run(TOKEN)
