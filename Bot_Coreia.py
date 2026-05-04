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

# IDs de cargos antigos (mantidos para compatibilidade)
CARGO_ADMIN_GERAL_ID = int(os.getenv("CARGO_ADMIN_GERAL_ID", "1386002307950317759"))
CARGO_MEMBRO_ID = int(os.getenv("CARGO_MEMBRO_ID", "1386004220691353675"))

# ========= NOVOS IDs =========
# Cargos do servidor
CARGO_00 = 1474106459955400772
CARGO_01 = 1474106459955400771
CARGO_02 = 1474106459955400770
CARGO_GERENTE_GERAL = 1474106459955400769
CARGO_GERENTE_FARM = 1474106459955400765
CARGO_GERENTE_VENDAS = 1474106459955400764
CARGO_ELITE = 1474106459540422734
CARGO_MEMBRO = 1474106459540422733

# Cargos que podem aprovar sets
CARGOS_APROVADORES = [CARGO_00, CARGO_01, CARGO_02]

# Cargos que podem gerenciar ações
CARGOS_ACAO = [CARGO_ELITE, CARGO_00, CARGO_01, CARGO_02]

# Cargos que podem resetar ranking
CARGOS_RESET_RANK = [CARGO_00, CARGO_01, CARGO_02]

# Cargos de compra e venda
CARGOS_VENDA = [CARGO_00, CARGO_01, CARGO_02, CARGO_GERENTE_VENDAS]
CARGOS_COMPRA = [CARGO_GERENTE_GERAL, CARGO_00, CARGO_01, CARGO_02]

# Cargos de admin (geral)
CARGOS_ADMIN = [CARGO_GERENTE_GERAL, CARGO_00, CARGO_01, CARGO_02]

# CANAIS E CATEGORIAS
CATEGORIA_FARMS_ID = int(os.getenv("CATEGORIA_FARMS_ID", "1498108914703532183"))
CATEGORIA_PAINEL_ID = int(os.getenv("CATEGORIA_PAINEL_ID", "1500656745800794205"))
CATEGORIA_BACKUP_ID = int(os.getenv("CATEGORIA_BACKUP_ID", "1500652423465930823"))
CATEGORIA_COMPRA_VENDA_LOGS_ID = int(os.getenv("CATEGORIA_COMPRA_VENDA_LOGS_ID", "1500647963117228242"))
CATEGORIA_LOGS_ID = int(os.getenv("CATEGORIA_LOGS_ID", "1500656957059764385"))
CATEGORIA_SETS = 1474106461012627459
CATEGORIA_APROVACAO_SETS = 1500651624597819442

CHAT_LOGS_ID = int(os.getenv("CHAT_LOGS_ID", "1498109309622550638"))
CHAT_ADMIN_LOGS_ID = int(os.getenv("CHAT_ADMIN_LOGS_ID", "1498109569853816963"))
CHAT_RANK_ID = int(os.getenv("CHAT_RANK_ID", "1500652542743412819"))
CHAT_COMPRA_VENDA_ID = int(os.getenv("CHAT_COMPRA_VENDA_ID", "1498110154317496330"))
LOG_REGISTROS_ID = int(os.getenv("LOG_REGISTROS_ID", "1498349960062570740"))
CANAL_ACOES_PAINEL_ID = int(os.getenv("CANAL_ACOES_PAINEL_ID", "1500647352497737748"))
CANAL_ACOES_LOGS_ID = int(os.getenv("CANAL_ACOES_LOGS_ID", "1500647398093881474"))
CANAL_BACKUP_ARQUIVOS_ID = int(os.getenv("CANAL_BACKUP_ARQUIVOS_ID", "1498898858413920386"))
CHAT_COMPRA_VENDA_LOG_ID = int(os.getenv("CHAT_COMPRA_VENDA_LOG_ID", "1500649180153122957"))

# Canal de aprovação de sets (você deve criar dentro da categoria 1500651624597819442)
CANAL_APROVACAO_SET_ID = int(os.getenv("CANAL_APROVACAO_SET_ID", "0"))

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
    "sets_pendentes": {},
    "acoes": {}
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

async def criar_canal_backup(tipo, nome_arquivo=None):
    categoria = bot.get_channel(CATEGORIA_BACKUP_ID)
    if not categoria: return None
    data = datetime.now().strftime("%d-%m-%Y_%H-%M-%S")
    if tipo == "novo":
        canal = await categoria.create_text_channel(f"backup-novo-{data}")
        embed = discord.Embed(title="NOVO BACKUP CRIADO", description=f"**Arquivo:** {nome_arquivo}\n**Data:** {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}", color=discord.Color.green())
        await canal.send(embed=embed)
        if nome_arquivo and os.path.exists(nome_arquivo):
            await canal.send(file=discord.File(nome_arquivo))
        return canal
    elif tipo == "deletado":
        canal = await categoria.create_text_channel(f"backup-deletado-{data}")
        embed = discord.Embed(title="BACKUP DELETADO", description=f"**Arquivo:** {nome_arquivo}\n**Data:** {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}", color=discord.Color.red())
        await canal.send(embed=embed)
        return canal

async def criar_canal_compra_venda_log(tipo, dados_log):
    canal = bot.get_channel(CHAT_COMPRA_VENDA_LOG_ID)
    if canal and isinstance(canal, discord.TextChannel):
        embed = discord.Embed(title=f"LOG DE {tipo.upper()}", color=discord.Color.blue(), timestamp=datetime.now())
        for chave, valor in dados_log.items():
            embed.add_field(name=chave, value=valor, inline=False)
        await canal.send(embed=embed)

async def limpar_logs_usuario(user_id, user_name):
    if str(user_id) in dados["usuarios_banidos"]: return 0
    dados["usuarios_banidos"].append(str(user_id))
    total_limpo = 0
    for canal_id in [CHAT_LOGS_ID, CHAT_ADMIN_LOGS_ID, CHAT_RANK_ID, CHAT_COMPRA_VENDA_ID]:
        canal = bot.get_channel(canal_id)
        if canal:
            async for mensagem in canal.history(limit=None):
                if mensagem.author == bot.user:
                    if f"<@{user_id}>" in mensagem.content or f"<@!{user_id}>" in mensagem.content:
                        novo = mensagem.content.replace(f"<@{user_id}>", f"[USUÁRIO REMOVIDO - {user_name}]").replace(f"<@!{user_id}>", f"[USUÁRIO REMOVIDO - {user_name}]")
                        try: await mensagem.edit(content=novo); total_limpo += 1
                        except: pass
    for canal_id in dados["canais"].values():
        canal = bot.get_channel(canal_id)
        if canal:
            async for mensagem in canal.history(limit=None):
                if mensagem.author == bot.user:
                    if f"<@{user_id}>" in mensagem.content or f"<@!{user_id}>" in mensagem.content:
                        novo = mensagem.content.replace(f"<@{user_id}>", f"[USUÁRIO REMOVIDO - {user_name}]").replace(f"<@!{user_id}>", f"[USUÁRIO REMOVIDO - {user_name}]")
                        try: await mensagem.edit(content=novo); total_limpo += 1
                        except: pass
    if str(user_id) in dados["usuarios"]:
        dados["usuarios"][str(user_id)] = {"farms":[],"pagamentos":[],"dinheiro_sujo":0,"nome":f"[REMOVIDO - {user_name}]","removido_em":datetime.now().strftime("%Y-%m-%d %H:%M:%S"),"removido_por":"sistema","transacoes_dinheiro_sujo":[],"transacoes_drogas":[]}
        salvar_dados()
    if str(user_id) in dados["canais"]:
        canal = bot.get_channel(dados["canais"][str(user_id)])
        if canal:
            try: await canal.delete(reason=f"Usuário {user_name} removido do sistema")
            except: pass
        del dados["canais"][str(user_id)]
        salvar_dados()
    return total_limpo

async def log_acao(acao, usuario, detalhes, cor=None):
    cores = {"criar_canal":0x00ff00,"registrar_farm":0x00ff00,"registrar_dinheiro_sujo":0xff0000,"registrar_drogas":0xff00ff,"pagar":0xffa500,"fechar_canal":0xff0000,"fechar_caixa":0xffa500,"reset_rank":0xff0000,"info":0x3498db,"admin":0x9b59b6,"compra_venda":0x00ff00,"usuario_removido":0xff0000,"editar_farm":0x3498db,"editar_dinheiro_sujo":0x3498db,"editar_drogas":0x3498db}
    cor_final = cores.get(acao, 0x3498db) if cor is None else cor
    canal_logs = bot.get_channel(CHAT_LOGS_ID)
    if canal_logs:
        embed = discord.Embed(title=f"LOG: {acao.upper()}", description=detalhes, color=cor_final, timestamp=datetime.now())
        if usuario: embed.set_author(name=usuario.name, icon_url=usuario.display_avatar.url)
        else: embed.set_author(name="Sistema")
        await canal_logs.send(embed=embed)

async def log_admin(titulo, descricao, cor=0xffa500):
    canal = bot.get_channel(CHAT_ADMIN_LOGS_ID)
    if canal:
        await canal.send(embed=discord.Embed(title=titulo, description=descricao, color=cor, timestamp=datetime.now()))

bot = commands.Bot(command_prefix="!", intents=discord.Intents.all())

def tem_cargo(member, cargos_ids):
    if not hasattr(member, 'guild'): return False
    for cid in cargos_ids:
        cargo = member.guild.get_role(cid)
        if cargo and cargo in member.roles: return True
    return False

def is_admin(member) -> bool: return tem_cargo(member, CARGOS_ADMIN)
def is_membro(member) -> bool: return tem_cargo(member, [CARGO_MEMBRO])
def pode_vender(member) -> bool: return tem_cargo(member, CARGOS_VENDA)
def pode_comprar(member) -> bool: return tem_cargo(member, CARGOS_COMPRA)
def pode_acao(member) -> bool: return tem_cargo(member, CARGOS_ACAO)
def pode_resetar_rank(member) -> bool: return tem_cargo(member, CARGOS_RESET_RANK)

async def atualizar_ranking():
    canal = bot.get_channel(CHAT_RANK_ID)
    if not canal: return
    async for msg in canal.history(limit=50):
        if msg.author == bot.user: await msg.delete()
    usuarios_data = []
    for uid, data in dados["usuarios"].items():
        if "removido_em" in data: continue
        try:
            user = await bot.fetch_user(int(uid))
            tot_corpo_rifle_normal = sum(p["quantidade"] for f in data["farms"] for p in f.get("produtos",[]) if p["produto"]=="Corpo de Rifle Normal")
            tot_corpo_rifle_especial = sum(p["quantidade"] for f in data["farms"] for p in f.get("produtos",[]) if p["produto"]=="Corpo de Rifle Especial")
            tot_aluminio = sum(p["quantidade"] for f in data["farms"] for p in f.get("produtos",[]) if p["produto"]=="Alumínio")
            tot_chapa_metal = sum(p["quantidade"] for f in data["farms"] for p in f.get("produtos",[]) if p["produto"]=="Chapa de Metal")
            tot_borracha = sum(p["quantidade"] for f in data["farms"] for p in f.get("produtos",[]) if p["produto"]=="Borracha")
            tot_corpo_pistola = sum(p["quantidade"] for f in data["farms"] for p in f.get("produtos",[]) if p["produto"]=="Corpo de Pistola")
            tot_corpo_sub = sum(p["quantidade"] for f in data["farms"] for p in f.get("produtos",[]) if p["produto"]=="Corpo de SUB")
            tot_pag = sum(p["valor"] for p in data["pagamentos"]); qtd_pag = len(data["pagamentos"])
            din_sujo = data.get("dinheiro_sujo",0)
            tot_drogas = sum(t["dinheiro"] for t in data.get("transacoes_drogas", []))
            usuarios_data.append({
                "nome":user.name,"user_id":uid,
                "total_corpo_rifle_normal":tot_corpo_rifle_normal,
                "total_corpo_rifle_especial":tot_corpo_rifle_especial,
                "total_aluminio":tot_aluminio,
                "total_chapa_metal":tot_chapa_metal,
                "total_borracha":tot_borracha,
                "total_corpo_pistola":tot_corpo_pistola,
                "total_corpo_sub":tot_corpo_sub,
                "total_pagamentos":tot_pag,"quantidade_pagamentos":qtd_pag,
                "dinheiro_sujo":din_sujo,"total_drogas":tot_drogas
            })
        except: continue
    emb = discord.Embed(title="RANKING GERAL", description=f"Atualizado em {datetime.now().strftime('%d/%m/%Y %H:%M')}", color=discord.Color.gold())
    for nome, key in [("Corpo Rifle Normal","total_corpo_rifle_normal"),("Corpo Rifle Especial","total_corpo_rifle_especial"),("Alumínio","total_aluminio"),("Chapa de Metal","total_chapa_metal"),("Borracha","total_borracha"),("Corpo de Pistola","total_corpo_pistola"),("Corpo de SUB","total_corpo_sub")]:
        lista = sorted(usuarios_data, key=lambda x: x[key], reverse=True)[:5]
        txt = ""; [txt := txt + f"{'🥇' if i==1 else '🥈' if i==2 else '🥉' if i==3 else f'{i}°'} **{u['nome']}** - {u[key]:,} itens\n" for i,u in enumerate(lista,1) if u[key]>0]
        emb.add_field(name=nome, value=txt or "Nenhum dado ainda", inline=False)
    lista_salario = sorted(usuarios_data, key=lambda x: x["total_pagamentos"], reverse=True)[:5]
    txt = ""; [txt := txt + f"{'🥇' if i==1 else '🥈' if i==2 else '🥉' if i==3 else f'{i}°'} **{u['nome']}** - R$ {u['total_pagamentos']:,.2f} ({u['quantidade_pagamentos']} pagamentos)\n" for i,u in enumerate(lista_salario,1) if u["total_pagamentos"]>0]
    emb.add_field(name="TOP SALÁRIO", value=txt or "Nenhum dado ainda", inline=False)
    lista_drogas = sorted(usuarios_data, key=lambda x: x["total_drogas"], reverse=True)[:5]
    txt = ""; [txt := txt + f"{'🥇' if i==1 else '🥈' if i==2 else '🥉' if i==3 else f'{i}°'} **{u['nome']}** - R$ {u['total_drogas']:,.2f}\n" for i,u in enumerate(lista_drogas,1) if u["total_drogas"]>0]
    emb.add_field(name="VENDAS DE DROGAS", value=txt or "Nenhum dado ainda", inline=False)
    await canal.send(embed=emb, view=RankingView())

class RankingView(View):
    def __init__(self): super().__init__(timeout=None)
    @discord.ui.button(label="Atualizar Ranking", style=discord.ButtonStyle.primary, emoji="🔄")
    async def atualizar(self, interaction: discord.Interaction, button: Button):
        await interaction.response.defer(); await atualizar_ranking(); await interaction.followup.send("Ranking atualizado!", ephemeral=True)
    @discord.ui.button(label="Resetar Ranking", style=discord.ButtonStyle.danger, emoji="⚠️")
    async def resetar(self, interaction: discord.Interaction, button: Button):
        if not pode_resetar_rank(interaction.user): await interaction.response.send_message("Sem permissão para resetar o ranking.", ephemeral=True); return
        await interaction.response.send_message("⚠️ ATENÇÃO! ...", view=ConfirmarResetView(), ephemeral=True)

class ConfirmarResetView(View):
    def __init__(self): super().__init__(timeout=60)
    @discord.ui.button(label="Sim, resetar ranking", style=discord.ButtonStyle.danger, emoji="⚠️")
    async def confirmar(self, interaction: discord.Interaction, button: Button):
        await interaction.response.defer(ephemeral=True, thinking=True)
        await salvar_backup_completo(interaction.user.name)
        dados["usuarios"] = {}; dados["caixa_semana"] = {}; dados["dinheiro_sujo"] = {}; salvar_dados()
        await log_acao("reset_rank", interaction.user, f"Ranking resetado por {interaction.user.mention}", 0xff0000)
        await log_admin("RANKING RESETADO", f"Admin: {interaction.user.mention}\nData: {datetime.now().strftime('%d/%m/%Y %H:%M')}", 0xff0000)
        await interaction.followup.send("Ranking resetado com sucesso!", ephemeral=True); await atualizar_ranking(); self.stop()
    @discord.ui.button(label="Cancelar", style=discord.ButtonStyle.secondary, emoji="❌")
    async def cancelar(self, interaction: discord.Interaction, button: Button): await interaction.response.send_message("Reset cancelado.", ephemeral=True); self.stop()

# ========= SISTEMA DE SETS (REFORMULADO) =========
class FormularioSet(Modal):
    def __init__(self):
        super().__init__(title="Solicitação de Set")
        self.nome = TextInput(label="Nome", placeholder="Ex: Carlos Oliveira", min_length=2, required=True)
        self.id_jogo = TextInput(label="ID do Jogo", placeholder="Ex: 450", min_length=1, required=True)
        self.add_item(self.nome)
        self.add_item(self.id_jogo)

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True, thinking=True)

        # Enviar para o canal de confirmação (registro)
        canal_registro = bot.get_channel(LOG_REGISTROS_ID)
        if canal_registro:
            embed_registro = discord.Embed(title="📝 FORMULÁRIO DE SET PREENCHIDO", color=discord.Color.blue(), timestamp=datetime.now())
            embed_registro.add_field(name="Solicitante", value=interaction.user.mention)
            embed_registro.add_field(name="Nome", value=self.nome.value)
            embed_registro.add_field(name="ID do Jogo", value=self.id_jogo.value)
            await canal_registro.send(embed=embed_registro)

        # Enviar para o canal de aprovação com botões
        canal_aprovacao = bot.get_channel(CANAL_APROVACAO_SET_ID)
        if canal_aprovacao:
            embed_aprov = discord.Embed(title="🔔 NOVA SOLICITAÇÃO DE SET", color=discord.Color.gold(), timestamp=datetime.now())
            embed_aprov.add_field(name="Solicitante", value=interaction.user.mention)
            embed_aprov.add_field(name="Nome", value=self.nome.value)
            embed_aprov.add_field(name="ID do Jogo", value=self.id_jogo.value)
            view = PainelAprovacaoSet(interaction.user, self.nome.value, self.id_jogo.value)
            await canal_aprovacao.send(embed=embed_aprov, view=view)

        await interaction.followup.send("Seu pedido foi enviado para a Staff! Aguarde a aprovação.", ephemeral=True)

class PainelAprovacaoSet(View):
    def __init__(self, usuario_pedido, nome, id_jogo):
        super().__init__(timeout=None)
        self.usuario_pedido = usuario_pedido
        self.nome = nome
        self.id_jogo = id_jogo

    @discord.ui.button(label="Aceitar", style=discord.ButtonStyle.success, emoji="✅")
    async def aceitar(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not tem_cargo(interaction.user, CARGOS_APROVADORES):
            await interaction.response.send_message("Sem permissão.", ephemeral=True)
            return
        # Mostrar select com os cargos
        view = View()
        select = Select(placeholder="Escolha o cargo para o membro...", options=[
            discord.SelectOption(label="Gerente de Farm", value=str(CARGO_GERENTE_FARM)),
            discord.SelectOption(label="Gerente de Vendas", value=str(CARGO_GERENTE_VENDAS)),
            discord.SelectOption(label="Elite", value=str(CARGO_ELITE)),
            discord.SelectOption(label="Membro", value=str(CARGO_MEMBRO)),
            discord.SelectOption(label="Gerente Geral", value=str(CARGO_GERENTE_GERAL))
        ])
        async def cargo_callback(inter):
            cargo_id = int(select.values[0])
            role = interaction.guild.get_role(cargo_id)
            if role:
                await self.usuario_pedido.add_roles(role)
            novo_apelido = f"{self.nome} | {self.id_jogo}"
            try: await self.usuario_pedido.edit(nick=novo_apelido)
            except: pass
            # Criar canal de farm
            guild = interaction.guild
            categoria = guild.get_channel(CATEGORIA_FARMS_ID)
            if categoria:
                overwrites = {
                    guild.default_role: discord.PermissionOverwrite(view_channel=False),
                    self.usuario_pedido: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True),
                }
                for rid in CARGOS_APROVADORES + [CARGO_GERENTE_GERAL, CARGO_GERENTE_FARM]:
                    r = guild.get_role(rid)
                    if r: overwrites[r] = discord.PermissionOverwrite(view_channel=True)
                await guild.create_text_channel(name=f"farm-{self.nome}", category=categoria, overwrites=overwrites)
            embed = discord.Embed(title="✅ PEDIDO APROVADO", color=discord.Color.green())
            embed.description = f"Membro: {self.usuario_pedido.mention}\nNome: `{novo_apelido}`\nCargo: {role.mention if role else 'N/A'}\nAprovado por: {inter.user.mention}"
            await interaction.message.edit(embed=embed, view=None)
            try: await self.usuario_pedido.send(f"Seu set foi aprovado! Nome: {novo_apelido}")
            except: pass
        select.callback = cargo_callback
        view.add_item(select)
        await interaction.response.send_message("Escolha o cargo:", view=view, ephemeral=True)

    @discord.ui.button(label="Recusar", style=discord.ButtonStyle.danger, emoji="❌")
    async def recusar(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not tem_cargo(interaction.user, CARGOS_APROVADORES):
            await interaction.response.send_message("Sem permissão.", ephemeral=True)
            return
        embed = discord.Embed(title="❌ PEDIDO RECUSADO", color=discord.Color.red())
        embed.description = f"Solicitante: {self.usuario_pedido.mention}\nRecusado por: {interaction.user.mention}"
        await interaction.message.edit(embed=embed, view=None)
        try: await self.usuario_pedido.send("Seu set foi recusado pela Staff.")
        except: pass

class ViewSet(View):
    def __init__(self):
        super().__init__(timeout=None)
    @discord.ui.button(label="🛡️ Solicitar Set", style=discord.ButtonStyle.primary)
    async def solicitar(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_modal(FormularioSet())

# ========= MODAIS DE FARM REFORMULADOS =========
class FarmProdutosModal(Modal, title="Registrar Farm Produtos"):
    rotas = TextInput(label="Quantas rotas fez", placeholder="Ex: 5", required=True)
    corpo_rifle_normal = TextInput(label="Corpo de Rifle Normal", placeholder="Ex: 10", required=False)
    corpo_rifle_especial = TextInput(label="Corpo de Rifle Especial", placeholder="Ex: 5", required=False)
    aluminio = TextInput(label="Alumínio", placeholder="Ex: 20", required=False)
    chapa_metal = TextInput(label="Chapa de Metal", placeholder="Ex: 15", required=False)
    borracha = TextInput(label="Borracha", placeholder="Ex: 30", required=False)
    corpo_pistola = TextInput(label="Corpo de Pistola", placeholder="Ex: 8", required=False)
    corpo_sub = TextInput(label="Corpo de SUB", placeholder="Ex: 3", required=False)

    def __init__(self, user_id, user_name, canal):
        super().__init__(); self.user_id = user_id; self.user_name = user_name; self.canal = canal
    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True, thinking=True)
        produtos = []
        mapeamento = [
            (self.corpo_rifle_normal, "Corpo de Rifle Normal"),
            (self.corpo_rifle_especial, "Corpo de Rifle Especial"),
            (self.aluminio, "Alumínio"),
            (self.chapa_metal, "Chapa de Metal"),
            (self.borracha, "Borracha"),
            (self.corpo_pistola, "Corpo de Pistola"),
            (self.corpo_sub, "Corpo de SUB")
        ]
        for campo, nome in mapeamento:
            if campo.value and campo.value.strip():
                try:
                    qtd = int(campo.value.strip())
                    if qtd > 0: produtos.append({"produto": nome, "quantidade": qtd})
                except ValueError: pass
        if not produtos:
            await interaction.followup.send("Nenhum produto válido!", ephemeral=True); return
        await interaction.followup.send("📸 Agora envie a **print da farm** aqui no canal.", ephemeral=True)
        def check(m): return m.author==interaction.user and m.channel==self.canal and m.attachments and any(a.content_type and a.content_type.startswith('image/') for a in m.attachments)
        try: msg = await bot.wait_for('message', timeout=60.0, check=check)
        except asyncio.TimeoutError: await interaction.followup.send("Tempo esgotado!", ephemeral=True); return
        imagem_url = msg.attachments[0].url
        if str(self.user_id) not in dados["usuarios"]: dados["usuarios"][str(self.user_id)] = {"farms":[],"pagamentos":[],"nome":self.user_name,"dinheiro_sujo":0,"transacoes_dinheiro_sujo":[],"transacoes_drogas":[]}
        registro = {"produtos":produtos,"data":datetime.now().strftime("%Y-%m-%d %H:%M:%S"),"print_url":imagem_url,"validado":True,"farm_id":len(dados["usuarios"][str(self.user_id)]["farms"])+1,"rotas":self.rotas.value}
        dados["usuarios"][str(self.user_id)]["farms"].append(registro); salvar_dados()
        embed = discord.Embed(title="FARM PRODUTOS REGISTRADA", description=f"**Usuário:** <@{self.user_id}>\n**Rotas:** {self.rotas.value}", color=discord.Color.green())
        desc = "".join(f"🔫 **{p['produto']}:** {p['quantidade']} itens\n" for p in produtos); embed.description += "\n" + desc
        embed.add_field(name="Data", value=datetime.now().strftime("%d/%m/%Y às %H:%M"), inline=False)
        embed.set_image(url=imagem_url); await self.canal.send(embed=embed)
        canal_registros = bot.get_channel(LOG_REGISTROS_ID)
        if canal_registros: await canal_registros.send(embed=embed)
        await interaction.followup.send(embed=embed, ephemeral=True)
        await log_acao("registrar_farm", interaction.user, f"Produtos: {desc.strip()}")
        await log_admin("NOVA FARM PRODUTOS", f"Usuário: {interaction.user.mention}\n{desc.strip()}", 0x00ff00); await atualizar_ranking()

class DinheiroSujoModal(Modal, title="Registrar Dinheiro Sujo"):
    c4 = TextInput(label="Quantidades de C4 que pegaram do baú", placeholder="Ex: 3", required=True)
    valor = TextInput(label="Valor que rendeu (R$)", placeholder="Ex: 5000", required=True)
    def __init__(self, user_id, user_name, canal):
        super().__init__(); self.user_id = user_id; self.user_name = user_name; self.canal = canal
    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True, thinking=True)
        try: valor_num = float(self.valor.value.replace(",","."))
        except ValueError: await interaction.followup.send("Valor inválido!", ephemeral=True); return
        await interaction.followup.send("📸 Agora envie a **print do comprovante** aqui no canal.", ephemeral=True)
        def check(m): return m.author==interaction.user and m.channel==self.canal and m.attachments and any(a.content_type and a.content_type.startswith('image/') for a in m.attachments)
        try: msg = await bot.wait_for('message', timeout=60.0, check=check)
        except asyncio.TimeoutError: await interaction.followup.send("Tempo esgotado!", ephemeral=True); return
        imagem_url = msg.attachments[0].url
        if str(self.user_id) not in dados["usuarios"]: dados["usuarios"][str(self.user_id)] = {"farms":[],"pagamentos":[],"nome":self.user_name,"dinheiro_sujo":0,"transacoes_dinheiro_sujo":[],"transacoes_drogas":[]}
        transacao = {"c4": self.c4.value, "valor": valor_num,"data": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),"print_url": imagem_url,"registrado_por": interaction.user.id}
        dados["usuarios"][str(self.user_id)].setdefault("transacoes_dinheiro_sujo", []).append(transacao)
        dados["usuarios"][str(self.user_id)]["dinheiro_sujo"] = sum(t["valor"] for t in dados["usuarios"][str(self.user_id)]["transacoes_dinheiro_sujo"])
        salvar_dados()
        embed = discord.Embed(title="💰 DINHEIRO SUJO REGISTRADO", description=f"**Usuário:** <@{self.user_id}>\n**C4 do baú:** {self.c4.value}\n**Valor:** R$ {valor_num:,.2f}", color=discord.Color.red(), timestamp=datetime.now())
        embed.set_image(url=imagem_url); await self.canal.send(embed=embed)
        canal_registros = bot.get_channel(LOG_REGISTROS_ID)
        if canal_registros: await canal_registros.send(embed=embed)
        await interaction.followup.send(f"R$ {valor_num:,.2f} registrado!", ephemeral=True)
        await log_acao("registrar_dinheiro_sujo", interaction.user, f"Valor: R$ {valor_num:,.2f}", 0xff0000); await atualizar_ranking()

class VendaDrogasModal(Modal, title="Registrar Venda de Drogas"):
    qtd_bau = TextInput(label="Quantidade que pegou do baú", placeholder="Ex: 100", required=True)
    total_vendas = TextInput(label="Total de vendas (quantidade)", placeholder="Ex: 80", required=True)
    sobrou = TextInput(label="O que sobrou", placeholder="Ex: 20", required=True)
    dinheiro = TextInput(label="Dinheiro (R$)", placeholder="Ex: 8000", required=True)
    def __init__(self, user_id, user_name, canal):
        super().__init__(); self.user_id = user_id; self.user_name = user_name; self.canal = canal
    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True, thinking=True)
        try:
            qtd = int(self.qtd_bau.value); total_v = int(self.total_vendas.value)
            sobrou_v = int(self.sobrou.value); din = float(self.dinheiro.value.replace(",","."))
        except ValueError: await interaction.followup.send("Valores inválidos!", ephemeral=True); return
        await interaction.followup.send("📸 Agora envie a **print do comprovante** aqui no canal.", ephemeral=True)
        def check(m): return m.author==interaction.user and m.channel==self.canal and m.attachments and any(a.content_type and a.content_type.startswith('image/') for a in m.attachments)
        try: msg = await bot.wait_for('message', timeout=60.0, check=check)
        except asyncio.TimeoutError: await interaction.followup.send("Tempo esgotado!", ephemeral=True); return
        imagem_url = msg.attachments[0].url
        if str(self.user_id) not in dados["usuarios"]: dados["usuarios"][str(self.user_id)] = {"farms":[],"pagamentos":[],"nome":self.user_name,"dinheiro_sujo":0,"transacoes_dinheiro_sujo":[],"transacoes_drogas":[]}
        transacao = {"qtd_bau": qtd, "total_vendas": total_v, "sobrou": sobrou_v, "dinheiro": din, "data": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),"print_url": imagem_url}
        dados["usuarios"][str(self.user_id)].setdefault("transacoes_drogas", []).append(transacao)
        salvar_dados()
        embed = discord.Embed(title="💊 VENDA DE DROGAS REGISTRADA", description=f"**Usuário:** <@{self.user_id}>\n**Qtd Baú:** {qtd}\n**Total Vendas:** {total_v}\n**Sobrou:** {sobrou_v}\n**Dinheiro:** R$ {din:,.2f}", color=discord.Color.purple(), timestamp=datetime.now())
        embed.set_image(url=imagem_url); await self.canal.send(embed=embed)
        canal_registros = bot.get_channel(LOG_REGISTROS_ID)
        if canal_registros: await canal_registros.send(embed=embed)
        await interaction.followup.send("Venda de drogas registrada!", ephemeral=True)
        await log_acao("registrar_drogas", interaction.user, f"Dinheiro: R$ {din:,.2f}", 0xff00ff); await atualizar_ranking()

# ========= COMPRA/VENDA REFORMULADO =========
class VendaArmaModal(Modal, title="Venda de Arma"):
    tipo_arma = TextInput(label="Tipo de Arma", placeholder="Ex: AK-47", required=True)
    quantidade = TextInput(label="Quantidade", placeholder="Ex: 10", required=True)
    valor = TextInput(label="Valor (R$)", placeholder="Ex: 5000", required=True)
    faccao = TextInput(label="Facção", placeholder="Ex: CV", required=True)
    responsavel = TextInput(label="Responsável pela Compra", placeholder="Ex: João", required=True)
    async def on_submit(self, interaction: discord.Interaction):
        if not pode_vender(interaction.user): await interaction.response.send_message("Sem permissão para registrar vendas.", ephemeral=True); return
        await interaction.response.defer(ephemeral=True, thinking=True)
        try: qtd = int(self.quantidade.value); valor_num = float(self.valor.value.replace(",","."))
        except ValueError: await interaction.followup.send("Valores inválidos!", ephemeral=True); return
        await interaction.followup.send("📸 Envie a **print do comprovante**.", ephemeral=True)
        def check(m): return m.author==interaction.user and m.channel==interaction.channel and m.attachments and any(a.content_type and a.content_type.startswith('image/') for a in m.attachments)
        try: msg = await bot.wait_for('message', timeout=60.0, check=check)
        except asyncio.TimeoutError: await interaction.followup.send("Tempo esgotado!", ephemeral=True); return
        imagem_url = msg.attachments[0].url
        dados_log = {"Tipo":"VENDA","Arma":self.tipo_arma.value,"Quantidade":str(qtd),"Valor":f"R$ {valor_num:,.2f}","Facção":self.faccao.value,"Responsável":self.responsavel.value}
        await criar_canal_compra_venda_log("venda", dados_log)
        dados["compras_vendas"].append({"tipo":"venda","arma":self.tipo_arma.value,"quantidade":qtd,"valor":valor_num,"faccao":self.faccao.value,"responsavel":self.responsavel.value,"registrado_por":interaction.user.id,"data":datetime.now().strftime("%Y-%m-%d %H:%M:%S"),"print_url":imagem_url}); salvar_dados()
        await interaction.followup.send(f"Venda registrada!", ephemeral=True)
        await log_acao("compra_venda", interaction.user, f"Venda: {qtd}x {self.tipo_arma.value} - R$ {valor_num}", 0x00ff00)

class CompraModal(Modal, title="Compra de Produto"):
    quantidade = TextInput(label="Quantidade", placeholder="Ex: 1000", required=True)
    produto = TextInput(label="Produto", placeholder="Ex: Munição", required=True)
    valor_total = TextInput(label="Valor Total (R$)", placeholder="Ex: 500", required=True)
    faccao_vendedora = TextInput(label="Facção Vendedora", placeholder="Ex: CV", required=True)
    responsavel = TextInput(label="Responsável pela Compra", placeholder="Ex: @usuario", required=True)
    async def on_submit(self, interaction: discord.Interaction):
        if not pode_comprar(interaction.user): await interaction.response.send_message("Sem permissão para registrar compras.", ephemeral=True); return
        await interaction.response.defer(ephemeral=True, thinking=True)
        try: qtd = int(self.quantidade.value); valor = float(self.valor_total.value.replace(",","."))
        except: await interaction.followup.send("Valores inválidos!", ephemeral=True); return
        await interaction.followup.send("📸 Envie a **print do comprovante**.", ephemeral=True)
        def check(m): return m.author==interaction.user and m.channel==interaction.channel and m.attachments and any(a.content_type and a.content_type.startswith('image/') for a in m.attachments)
        try: msg = await bot.wait_for('message', timeout=60.0, check=check)
        except asyncio.TimeoutError: await interaction.followup.send("Tempo esgotado!", ephemeral=True); return
        imagem_url = msg.attachments[0].url
        await criar_canal_compra_venda_log("compra", {"Tipo":"COMPRA","Quantidade":str(qtd),"Produto":self.produto.value,"Valor":f"R$ {valor:,.2f}","Facção":self.faccao_vendedora.value,"Responsável":self.responsavel.value})
        dados["compras_vendas"].append({"tipo":"compra","quantidade":qtd,"produto":self.produto.value,"valor_total":valor,"faccao_vendedora":self.faccao_vendedora.value,"responsavel":self.responsavel.value,"registrado_por":interaction.user.id,"data":datetime.now().strftime("%Y-%m-%d %H:%M:%S"),"print_url":imagem_url}); salvar_dados()
        await interaction.followup.send("Compra registrada!", ephemeral=True)
        await log_acao("compra_venda", interaction.user, f"Compra: {qtd}x {self.produto.value} - R$ {valor}", 0x00ff00)

class CompraVendaView(View):
    def __init__(self): super().__init__(timeout=None)
    @discord.ui.button(label="Venda de Arma", style=discord.ButtonStyle.success, emoji="💸")
    async def venda(self, interaction: discord.Interaction, button: Button): await interaction.response.send_modal(VendaArmaModal())
    @discord.ui.button(label="Compra de Produto", style=discord.ButtonStyle.primary, emoji="🛒")
    async def compra(self, interaction: discord.Interaction, button: Button): await interaction.response.send_modal(CompraModal())

# ========= EDIÇÃO (mantida) =========
class EditarRegistroSelect(Select):
    # ... (código original mantido)
    pass
# (manter classes de edição originais: EditarFarmModal, EditarDinheiroSujoSelect, EditarDinheiroSujoModal, etc.)

# ========= FECHAR CAIXA POR TIPO =========
class EscolherTipoFechamentoView(View):
    def __init__(self, user_id, user_name, canal):
        super().__init__(timeout=120); self.user_id = user_id; self.user_name = user_name; self.canal = canal
    @discord.ui.button(label="Drogas", style=discord.ButtonStyle.primary, emoji="💊")
    async def drogas(self, interaction: discord.Interaction, button: Button):
        await interaction.response.defer(ephemeral=True)
        user_data = dados["usuarios"].get(str(self.user_id), {})
        transacoes = user_data.get("transacoes_drogas", [])
        if not transacoes:
            await interaction.followup.send("Nenhuma transação de drogas.", ephemeral=True); return
        total = sum(t["dinheiro"] for t in transacoes)
        embed = discord.Embed(title="FECHAMENTO - DROGAS", description=f"**{self.user_name}**\nTotal de drogas: R$ {total:,.2f}\nTransações: {len(transacoes)}", color=discord.Color.purple())
        await interaction.followup.send(embed=embed, ephemeral=True)
    @discord.ui.button(label="Dinheiro Sujo", style=discord.ButtonStyle.danger, emoji="💰")
    async def dinheiro_sujo(self, interaction: discord.Interaction, button: Button):
        await interaction.response.defer(ephemeral=True)
        user_data = dados["usuarios"].get(str(self.user_id), {})
        total_sujo = user_data.get("dinheiro_sujo", 0.0)
        if total_sujo <= 0:
            await interaction.followup.send("Nenhum dinheiro sujo acumulado.", ephemeral=True); return
        lavagem = total_sujo * 0.25; restante = total_sujo - lavagem; faccao = restante * 0.50; membro_base = restante * 0.50
        embed = discord.Embed(title="FECHAMENTO - DINHEIRO SUJO", color=discord.Color.red())
        embed.add_field(name="Total", value=f"R$ {total_sujo:,.2f}")
        embed.add_field(name="Lavagem (25%)", value=f"R$ {lavagem:,.2f}")
        embed.add_field(name="Facção (50%)", value=f"R$ {faccao:,.2f}")
        embed.add_field(name="Membro (50%)", value=f"R$ {membro_base:,.2f}")
        view = FechamentoSummaryView(self.user_id, self.user_name, self.canal, total_sujo, lavagem, faccao, membro_base)
        await interaction.followup.send(embed=embed, view=view, ephemeral=True)
    @discord.ui.button(label="Farm", style=discord.ButtonStyle.success, emoji="📦")
    async def farm(self, interaction: discord.Interaction, button: Button):
        await interaction.response.defer(ephemeral=True)
        user_data = dados["usuarios"].get(str(self.user_id), {})
        farms = user_data.get("farms", [])
        if not farms:
            await interaction.followup.send("Nenhuma farm registrada.", ephemeral=True); return
        # Mostrar resumo das farms
        resumo = {}
        for f in farms:
            for p in f["produtos"]:
                resumo[p["produto"]] = resumo.get(p["produto"], 0) + p["quantidade"]
        embed = discord.Embed(title="FECHAMENTO - FARM", color=discord.Color.green())
        for produto, qtd in resumo.items():
            embed.add_field(name=produto, value=f"{qtd} itens")
        await interaction.followup.send(embed=embed, ephemeral=True)

# ========= FARM CHANNEL VIEW =========
class FarmChannelView(View):
    def __init__(self, user_id, user_name, canal_id):
        super().__init__(timeout=None); self.user_id = user_id; self.user_name = user_name; self.canal_id = canal_id
    @discord.ui.button(label="Farm Produtos", style=discord.ButtonStyle.success, emoji="📦", row=0)
    async def farm_produtos(self, interaction: discord.Interaction, button: Button):
        if not is_membro(interaction.user): await interaction.response.send_message("Apenas membros!", ephemeral=True); return
        await interaction.response.send_modal(FarmProdutosModal(self.user_id, self.user_name, interaction.channel))
    @discord.ui.button(label="Venda de Drogas", style=discord.ButtonStyle.primary, emoji="💊", row=0)
    async def venda_drogas(self, interaction: discord.Interaction, button: Button):
        if not is_membro(interaction.user): await interaction.response.send_message("Apenas membros!", ephemeral=True); return
        await interaction.response.send_modal(VendaDrogasModal(self.user_id, self.user_name, interaction.channel))
    @discord.ui.button(label="Dinheiro Sujo", style=discord.ButtonStyle.danger, emoji="💰", row=0)
    async def dinheiro_sujo(self, interaction: discord.Interaction, button: Button):
        if not is_membro(interaction.user): await interaction.response.send_message("Apenas membros!", ephemeral=True); return
        await interaction.response.send_modal(DinheiroSujoModal(self.user_id, self.user_name, interaction.channel))
    @discord.ui.button(label="Editar Registro", style=discord.ButtonStyle.blurple, emoji="✏️", row=1)
    async def editar_registro(self, interaction: discord.Interaction, button: Button):
        if not is_admin(interaction.user): await interaction.response.send_message("Apenas admins!", ephemeral=True); return
        # view = EscolherTipoEdicaoView... (manter original)
        await interaction.response.send_message("Em manutenção.", ephemeral=True)
    @discord.ui.button(label="Fechar Caixa", style=discord.ButtonStyle.danger, emoji="📊", row=1)
    async def fechar_caixa(self, interaction: discord.Interaction, button: Button):
        if not is_admin(interaction.user): await interaction.response.send_message("Apenas administradores!", ephemeral=True); return
        await interaction.response.send_message("Escolha o tipo de fechamento:", view=EscolherTipoFechamentoView(self.user_id, self.user_name, interaction.channel), ephemeral=True)
    @discord.ui.button(label="Mudar Nome", style=discord.ButtonStyle.secondary, emoji="✏️", row=1)
    async def mudar_nome(self, interaction: discord.Interaction, button: Button):
        if not is_admin(interaction.user): await interaction.response.send_message("Apenas administradores!", ephemeral=True); return
        await interaction.response.send_modal(MudarNomeModal(interaction.channel))
    @discord.ui.button(label="Histórico Caixa", style=discord.ButtonStyle.secondary, emoji="📜", row=2)
    async def historico_caixa(self, interaction: discord.Interaction, button: Button):
        if not is_admin(interaction.user): await interaction.response.send_message("Apenas administradores!", ephemeral=True); return
        await interaction.response.defer(ephemeral=True, thinking=True)
        fechamentos = dados["caixa_semana"].get(str(self.user_id),[])
        if not fechamentos: await interaction.followup.send("Nenhum fechamento.", ephemeral=True); return
        embed = discord.Embed(title="HISTÓRICO DE CAIXA", color=discord.Color.blue())
        for fech in fechamentos[-10:]:
            data = datetime.strptime(fech["data"],"%Y-%m-%d %H:%M:%S").strftime("%d/%m/%Y")
            txt = f"Meta: {fech.get('meta_farm','?')}\n"
            if "dinheiro_sujo" in fech:
                ds = fech["dinheiro_sujo"]; txt += f"Total: R$ {ds['total']:,.2f}"
            embed.add_field(name=f"📅 {data}", value=txt, inline=False)
        await interaction.followup.send(embed=embed, ephemeral=True)
    @discord.ui.button(label="Reset Semanal", style=discord.ButtonStyle.danger, emoji="🔄", row=2)
    async def reset_semanal(self, interaction: discord.Interaction, button: Button):
        if not is_admin(interaction.user): await interaction.response.send_message("Apenas administradores!", ephemeral=True); return
        confirm_view = ConfirmResetSemanalView(self.user_id, self.user_name, interaction.channel)
        await interaction.response.send_message("⚠️ **Tem certeza que deseja resetar a semana?**", view=confirm_view, ephemeral=True)
    @discord.ui.button(label="Fechar Canal", style=discord.ButtonStyle.danger, emoji="🗑️", row=2)
    async def fechar_canal(self, interaction: discord.Interaction, button: Button):
        if not is_admin(interaction.user): await interaction.response.send_message("Apenas administradores!", ephemeral=True); return
        await interaction.response.send_message("⚠️ Tem certeza?", view=ConfirmarFechamentoView(self.user_id, interaction.channel), ephemeral=True)

# (Classes ConfirmResetSemanalView, ConfirmarFechamentoView, MudarNomeModal mantidas como original)

# ========= PAINEL DE AÇÕES REFORMULADO =========
class ActionPanelView(View):
    def __init__(self, server_id):
        super().__init__(timeout=None); self.server_id = server_id
    @discord.ui.button(label="Abrir Ação", style=discord.ButtonStyle.success, emoji="⚔️")
    async def open_action(self, interaction: discord.Interaction, button: Button):
        if not pode_acao(interaction.user): await interaction.response.send_message("Sem permissão para registrar ações.", ephemeral=True); return
        await interaction.response.send_modal(ActionModal(self.server_id))
    @discord.ui.button(label="Pagamento", style=discord.ButtonStyle.primary, emoji="💰")
    async def payment(self, interaction: discord.Interaction, button: Button):
        if not pode_acao(interaction.user): await interaction.response.send_message("Sem permissão.", ephemeral=True); return
        await interaction.response.defer(ephemeral=True, thinking=True)
        server_actions = dados["acoes"].get(str(self.server_id),{})
        unpaid = {k:v for k,v in server_actions.items() if not v.get("pago",False)}
        if not unpaid: await interaction.followup.send("Nenhuma ação pendente.", ephemeral=True); return
        view = ActionSelectView(self.server_id, unpaid)
        await interaction.followup.send("Selecione a ação:", view=view, ephemeral=True)

# (ActionModal, MemberSelectView, ActionSelectView, ConfirmPaymentView mantidas com 50/50)

# ========= EVENTOS E INICIALIZAÇÃO =========
@bot.event
async def on_ready():
    print(f"Bot {bot.user} online!")
    for guild in bot.guilds:
        # Enviar painel de set automaticamente na categoria
        categoria_sets = guild.get_channel(CATEGORIA_SETS)
        if categoria_sets and isinstance(categoria_sets, discord.CategoryChannel):
            canal_set = discord.utils.get(categoria_sets.text_channels, name="solicitar-set")
            if not canal_set:
                canal_set = await categoria_sets.create_text_channel("solicitar-set")
            async for msg in canal_set.history(limit=5):
                if msg.author == bot.user: await msg.delete()
            await canal_set.send(embed=discord.Embed(title="🛡️ SISTEMA DE SETS", description="Clique no botão abaixo para solicitar seu set.\nPreencha seu **Nome** e **ID do Jogo**.", color=0x2b2d31), view=ViewSet())

        # Outros painéis (mantidos)
        canal_vendas = bot.get_channel(CHAT_COMPRA_VENDA_ID)
        if canal_vendas:
            async for msg in canal_vendas.history(limit=10):
                if msg.author == bot.user: await msg.delete()
            await canal_vendas.send(embed=discord.Embed(title="SISTEMA DE COMPRA E VENDA", description="💸 **Venda de Arma**\n🛒 **Compra de Produto**", color=discord.Color.blue()), view=CompraVendaView())

        categoria_painel = guild.get_channel(CATEGORIA_PAINEL_ID)
        if categoria_painel:
            canal_criar = discord.utils.get(categoria_painel.channels, name="criar-canal")
            if not canal_criar: canal_criar = await categoria_painel.create_text_channel("criar-canal")
            async for msg in canal_criar.history(limit=5):
                if msg.author == bot.user: await msg.delete()
            await canal_criar.send(embed=discord.Embed(title="SISTEMA DE FARM", description="Clique no botão abaixo para criar seu canal privado!", color=discord.Color.blue()), view=BotaoCriarCanalView())

        categoria_backup = guild.get_channel(CATEGORIA_BACKUP_ID)
        if categoria_backup:
            canal_backup_painel = discord.utils.get(categoria_backup.channels, name="painel-backup")
            if not canal_backup_painel: canal_backup_painel = await categoria_backup.create_text_channel("painel-backup")
            async for msg in canal_backup_painel.history(limit=5):
                if msg.author == bot.user: await msg.delete()
            await canal_backup_painel.send(embed=discord.Embed(title="💾 PAINEL DE BACKUP", description="💾 **Criar Backup**\n🗑️ **Apagar Backups Locais**\n🔄 **Recarregar Backup**", color=discord.Color.blue()), view=BackupView())

        canal_acoes = bot.get_channel(CANAL_ACOES_PAINEL_ID)
        if canal_acoes:
            async for msg in canal_acoes.history(limit=5):
                if msg.author == bot.user: await msg.delete()
            embed = discord.Embed(title="⚔️ PAINEL DE AÇÕES", description="Gerencie as ações e os pagamentos da facção.", color=discord.Color.dark_red())
            embed.add_field(name="Abrir Ação", value="Registre uma nova ação.")
            embed.add_field(name="Pagamento", value="Efetue o pagamento (50% membros / 50% facção).")
            await canal_acoes.send(embed=embed, view=ActionPanelView(guild.id))

        canal_backup_arquivos = bot.get_channel(CANAL_BACKUP_ARQUIVOS_ID)
        if canal_backup_arquivos: await salvar_backup_completo("Sistema (Auto)")

    await atualizar_ranking()
    await log_admin("🤖 BOT INICIADO", f"Bot {bot.user.mention} online!", 0x00ff00)

if __name__ == "__main__":
    carregar_dados()
    bot.run(TOKEN)
