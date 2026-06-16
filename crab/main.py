# -*- coding: utf-8 -*-
"""
EVERYTHING IS CRAB - Mapa Quadrado, 3 Biomas, Bosses Rotativos
"""
import pygame, sys, math, random, asyncio

# ══════════════════════════════════════════════
#  CONFIG
# ══════════════════════════════════════════════
SW, SH     = 960, 640
MAPA_S     = 4800          # mapa QUADRADO 4800x4800
FPS        = 60
DURACAO    = 600           # 10 min
BOSS_CADA  = 90            # boss a cada 90s

# Mapa quadrado dividido em 4 quadrantes:
#   [FLORESTA | DESERTO ]
#   [DESERTO  |  NEVE   ]
# Fronteira no meio: x=2400, y=2400
MEIO = MAPA_S // 2

# Regioes dos biomas (retangulos dentro do quadrado)
BIOMA_REGIOES = {
    "floresta": (0,       0,       MEIO,   MEIO),    # top-left
    "deserto":  (MEIO,    0,       MAPA_S, MEIO),    # top-right  + bottom-left
    "neve":     (MEIO,    MEIO,    MAPA_S, MAPA_S),  # bottom-right
}
# Para o deserto ocupar o centro também:
# Vamos usar quadrantes definidos por ângulo a partir do centro
# Floresta: NW, Deserto: NE+SW (cruz central), Neve: SE
# Simples: dividimos o mapa em 4 quadrantes e atribuímos biomas
QUADRANTES = {
    "floresta": (0,     0,     MEIO,   MEIO),
    "deserto":  (MEIO,  0,     MAPA_S, MEIO),
    "neve":     (0,     MEIO,  MEIO,   MAPA_S),
    "pantano":  (MEIO,  MEIO,  MAPA_S, MAPA_S),
}
# Vamos usar só 3 biomas mas com layout em L:
# floresta=NW, deserto=NE, neve=S (toda a metade inferior)
BIOMAS_LAYOUT = {
    "floresta": (0,     0,     MEIO,   MEIO),
    "deserto":  (MEIO,  0,     MAPA_S, MEIO),
    "neve":     (0,     MEIO,  MAPA_S, MAPA_S),
}

# ══════════════════════════════════════════════
#  CORES
# ══════════════════════════════════════════════
C = {
    "floresta_bg": (28,  52,  22),
    "floresta_g1": (38,  68,  28),
    "floresta_g2": (50,  80,  32),
    "deserto_bg":  (195,160,  90),
    "deserto_g1":  (210,175, 100),
    "deserto_g2":  (180,145,  75),
    "neve_bg":     (215,228, 248),
    "neve_g1":     (195,215, 240),
    "neve_g2":     (235,243, 255),
    "player":      ( 70,130, 220),
    "fruta":       ( 55,205,  55),
    "cogumelo":    (165, 65, 205),
    "carne":       (205, 65,  45),
    "texto":       (238,232, 208),
    "ouro":        (242,198,  38),
    "aviso":       (228, 55,  18),
    "hp":          (198, 38,  38),
    "xp":          ( 55,195,  75),
    "boss":        (198, 28,  28),
    "borda":       ( 80, 60,  30),
}

def ipc(a,b,t): return tuple(max(0,min(255,int(a[i]+(b[i]-a[i])*t))) for i in range(3))
def dist(ax,ay,bx,by): return math.hypot(bx-ax,by-ay)
def clamp(v,a,b): return max(a,min(b,v))
def rnd(a,b): return a+random.random()*(b-a)
def rndI(a,b): return random.randint(a,b)
def choice(l): return l[random.randint(0,len(l)-1)]

def get_bioma(x,y):
    if y < MEIO:
        return "floresta" if x < MEIO else "deserto"
    return "neve"

# ══════════════════════════════════════════════
#  CAMERA
# ══════════════════════════════════════════════
class Camera:
    def __init__(self):
        self.x = 0.0
        self.y = 0.0

    def seguir(self, jx, jy):
        ax = clamp(jx - SW//2, 0, MAPA_S - SW)
        ay = clamp(jy - SH//2, 0, MAPA_S - SH)
        self.x += (ax - self.x) * 0.12
        self.y += (ay - self.y) * 0.12

    def t(self, wx, wy):               # mundo -> tela
        return wx - self.x, wy - self.y

    def vis(self, wx, wy, m=80):
        sx, sy = self.t(wx, wy)
        return -m < sx < SW+m and -m < sy < SH+m

# ══════════════════════════════════════════════
#  EVOLUÇÕES
# ══════════════════════════════════════════════
EVOLUCOES = [
    {"nome":"Patas Ageis",      "ic":"[PE]",    "rar":1,"desc":"+35% velocidade",    "vel":1.35},
    {"nome":"Nadadeiras",       "ic":"[PEIXE]", "rar":1,"desc":"+25% velocidade",    "vel":1.25},
    {"nome":"Asas",             "ic":"[ASA]",   "rar":2,"desc":"+65% velocidade",    "vel":1.65},
    {"nome":"Propulsao",        "ic":"[FOGT]",  "rar":3,"desc":"+100% velocidade",   "vel":2.0},
    {"nome":"Garras Afiadas",   "ic":"[GARRA]", "rar":1,"desc":"+50% dano",          "dano":1.5},
    {"nome":"Ferrao Venenoso",  "ic":"[VEN]",   "rar":2,"desc":"+80%dano+veneno",    "dano":1.8,"veneno":True},
    {"nome":"Pincas",           "ic":"[CRAB]",  "rar":2,"desc":"+60%dano +20vida",   "dano":1.6,"vida":20},
    {"nome":"Mandibulas",       "ic":"[DENTE]", "rar":1,"desc":"+40% dano",          "dano":1.4},
    {"nome":"Concha Dura",      "ic":"[CONCHA]","rar":1,"desc":"+80 vida max",       "vida":80},
    {"nome":"Pele Grossa",      "ic":"[COURO]", "rar":1,"desc":"-30% dano receb",   "def":0.70},
    {"nome":"Armadura Osso",    "ic":"[OSSO]",  "rar":2,"desc":"-50% dano receb",   "def":0.50},
    {"nome":"Espinhos",         "ic":"[ESPIN]", "rar":2,"desc":"Reflete 25% dano",  "espinhos":True},
    {"nome":"Corpo Maior",      "ic":"[MAIOR]", "rar":1,"desc":"+35%tam +60vida",   "tamanho":1.35,"vida":60},
    {"nome":"Regeneracao",      "ic":"[REGEN]", "rar":2,"desc":"Regen +3 vida/s",   "regen":3},
    {"nome":"Regen Epica",      "ic":"[REGEN2]","rar":3,"desc":"Regen +8 vida/s",   "regen":8},
    {"nome":"Boca Gulosa",      "ic":"[BOCA]",  "rar":1,"desc":"+40% XP comida",    "xpBonus":1.4},
    {"nome":"Lingua Longa",     "ic":"[LING]",  "rar":1,"desc":"Raio coletax1.6",   "raioColeta":1.6},
    {"nome":"Camuflagem",       "ic":"[CAMU]",  "rar":2,"desc":"Menos visivel",     "camuflagem":True},
    {"nome":"Aura de Fogo",     "ic":"[FOGO]",  "rar":3,"desc":"Queima ao redor",   "auraFogo":True},
    {"nome":"Carcinizacao",     "ic":"[CRAB2]", "rar":3,"desc":"VIRA CARANGUEJO",   "dano":1.3,"vel":1.15,"vida":40,"def":0.88},
    {"nome":"Instinto Predador","ic":"[PRED]",  "rar":3,"desc":"+80%dano+30%vel",   "dano":1.8,"vel":1.3},
    {"nome":"Dash",             "ic":"[DASH]",  "rar":2,"desc":"Dash com Shift",    "dash":True},
    {"nome":"Membrana Solar",   "ic":"[SOL]",   "rar":3,"desc":"Regen5+20%vel",     "regen":5,"vel":1.2},
    {"nome":"Visao Aguia",      "ic":"[OLHO]",  "rar":2,"desc":"Mais percepcao",    "percepcao":1.6},
    {"nome":"Veneno em Area",   "ic":"[NUVEM]", "rar":3,"desc":"Nuvem venenosa",    "auraVeneno":True},
]

# Pool de bosses — fila rotativa, mesmo boss só volta depois de 5 outros
POOL_BOSSES = [
    # floresta
    {"nome":"Rei Lobo da Floresta",  "bioma":"floresta","cor":(70,70,85), "cor2":(140,140,155),"partes":["cauda_longa","chifre","juba"],"vm_base":700},
    {"nome":"Abelha Rainha Gigante", "bioma":"floresta","cor":(230,195,15),"cor2":(40,40,40),  "partes":["asas_boss","listras_boss"],  "vm_base":620},
    {"nome":"Grande Caracol Antigo", "bioma":"floresta","cor":(90,150,55), "cor2":(170,230,90),"partes":["concha_boss","chifre"],      "vm_base":580},
    # deserto
    {"nome":"Cobra Rei do Deserto",  "bioma":"deserto", "cor":(55,150,35),"cor2":(190,230,70),"partes":["cauda_longa","serpente_boss"],"vm_base":720},
    {"nome":"Leao das Dunas",        "bioma":"deserto", "cor":(215,165,45),"cor2":(170,115,15),"partes":["juba","chifre","cauda_longa"],"vm_base":780},
    {"nome":"Tatu Colossal",         "bioma":"deserto", "cor":(115,95,65),"cor2":(175,155,105),"partes":["armadura_boss","chifre"],   "vm_base":650},
    # neve
    {"nome":"Urso Polar Ancestral",  "bioma":"neve",    "cor":(235,242,255),"cor2":(175,188,208),"partes":["grande_boss","chifre"],   "vm_base":820},
    {"nome":"Leopardo das Sombras",  "bioma":"neve",    "cor":(195,185,155),"cor2":(55,38,18),"partes":["manchas_boss","cauda_longa"],"vm_base":690},
    {"nome":"Morsa Glacial",         "bioma":"neve",    "cor":(132,142,155),"cor2":(195,205,218),"partes":["gordo_boss","chifre"],    "vm_base":660},
    # mistos (aparecem em qualquer bioma)
    {"nome":"Raposa Sombria",        "bioma":"todos",   "cor":(180,40,180),"cor2":(220,120,220),"partes":["cauda_longa","asas_boss"], "vm_base":750},
    {"nome":"O Caranguejo Primordial","bioma":"todos",  "cor":(210,55,15),"cor2":(240,100,45),"partes":["pincas_boss","chifre"],      "vm_base":900},
]

def escolher_evos(n=3, pool=None):
    if pool is None: pool = EVOLUCOES
    p = list(pool)
    w = [{1:12,2:4,3:1}[e["rar"]] for e in p]
    out = []
    for _ in range(min(n, len(p))):
        total = sum(w); r = random.random()*total; acc = 0
        for i,(e,wi) in enumerate(zip(p,w)):
            acc += wi
            if r <= acc: out.append(e); p.pop(i); w.pop(i); break
    return out

EVOLUCOES_BOSS = [
    {"nome":"Coroa do Rei",      "ic":"[COROA]", "rar":3,"desc":"Todos stats+25%",   "dano":1.25,"vel":1.25,"vida":60,"def":0.80},
    {"nome":"Coracao de Boss",   "ic":"[CORC]",  "rar":3,"desc":"+200vida regen10",  "vida":200,"regen":10},
    {"nome":"Furia Primordial",  "ic":"[FURIA]", "rar":3,"desc":"+150% dano",        "dano":2.5},
    {"nome":"Escudo Divino",     "ic":"[ESCUDO]","rar":3,"desc":"-80% dano receb",   "def":0.20},
    {"nome":"Omega Caranguejo",  "ic":"[OMEGA]", "rar":3,"desc":"A FORMA FINAL",     "dano":2.0,"vel":1.4,"vida":150,"def":0.60},
]

# ══════════════════════════════════════════════
#  DADOS DOS ANIMAIS
# ══════════════════════════════════════════════
ANIMAIS_BIOMA = {
    "floresta":[
        {"tipo":"abelha",  "cor":(238,198,18),"cor2":(45,45,45), "cauda":False,"patas":3,"xpBase":18,"danoBase":8, "asas":True},
        {"tipo":"esquilo", "cor":(158,88,38), "cor2":(218,178,128),"cauda":True,"patas":2,"xpBase":15,"danoBase":6},
        {"tipo":"caracol", "cor":(98,158,58), "cor2":(178,238,98),"cauda":False,"patas":0,"xpBase":12,"danoBase":4,"lento":True},
        {"tipo":"lobo",    "cor":(78,78,88),  "cor2":(148,148,158),"cauda":True,"patas":2,"xpBase":30,"danoBase":18,"rapido":True},
        {"tipo":"raposa",  "cor":(218,98,18), "cor2":(18,18,18),  "cauda":True,"patas":2,"xpBase":22,"danoBase":12},
    ],
    "deserto":[
        {"tipo":"cobra",   "cor":(58,158,38), "cor2":(198,238,78),"cauda":True,"patas":0,"xpBase":20,"danoBase":14,"serpente":True},
        {"tipo":"tatu",    "cor":(118,98,68), "cor2":(178,158,108),"cauda":True,"patas":2,"xpBase":16,"danoBase":8,"armadura":True},
        {"tipo":"zebra",   "cor":(238,238,238),"cor2":(18,18,18), "cauda":True,"patas":2,"xpBase":20,"danoBase":10,"listras":True},
        {"tipo":"leao",    "cor":(218,168,48),"cor2":(178,118,18),"cauda":True,"patas":2,"xpBase":35,"danoBase":22,"juba":True},
        {"tipo":"raposa",  "cor":(198,138,58),"cor2":(178,98,28), "cauda":True,"patas":2,"xpBase":22,"danoBase":12},
    ],
    "neve":[
        {"tipo":"pinguim", "cor":(18,18,22),  "cor2":(238,238,238),"cauda":False,"patas":1,"xpBase":14,"danoBase":6},
        {"tipo":"leopardo","cor":(198,188,158),"cor2":(58,38,18),  "cauda":True,"patas":2,"xpBase":28,"danoBase":20,"manchas":True},
        {"tipo":"foca",    "cor":(138,148,158),"cor2":(198,208,218),"cauda":True,"patas":0,"xpBase":16,"danoBase":8,"gordo":True},
        {"tipo":"urso",    "cor":(238,243,255),"cor2":(178,188,208),"cauda":True,"patas":2,"xpBase":38,"danoBase":25,"grande":True},
        {"tipo":"raposa",  "cor":(243,246,253),"cor2":(198,208,228),"cauda":True,"patas":2,"xpBase":22,"danoBase":12},
    ],
}

# ══════════════════════════════════════════════
#  FUNDO
# ══════════════════════════════════════════════
fundo_surf = None

def gerar_fundo():
    global fundo_surf
    fundo_surf = pygame.Surface((MAPA_S, MAPA_S))
    rng = random.Random(2025)

    for bioma,(bx1,by1,bx2,by2) in BIOMAS_LAYOUT.items():
        bg = C[bioma+"_bg"]; g1 = C[bioma+"_g1"]; g2 = C[bioma+"_g2"]
        pygame.draw.rect(fundo_surf, bg, (bx1,by1,bx2-bx1,by2-by1))

        # manchas de terreno
        for _ in range(180):
            mx = bx1+rng.randint(0,bx2-bx1)
            my = by1+rng.randint(0,by2-by1)
            mr = rng.randint(30,130)
            s = pygame.Surface((mr*2,mr*2), pygame.SRCALPHA)
            cc = g1 if rng.random()<0.5 else g2
            pygame.draw.ellipse(s,(*cc,105),(0,0,mr*2,mr*2))
            fundo_surf.blit(s,(mx-mr,my-mr))

        if bioma == "floresta":
            for _ in range(80):
                tx=bx1+rng.randint(60,bx2-bx1-60); ty=by1+rng.randint(60,by2-by1-60)
                tr=rng.randint(20,40)
                pygame.draw.circle(fundo_surf,(28,88,18),(tx,ty),tr)
                pygame.draw.circle(fundo_surf,(48,118,28),(tx-5,ty-5),tr//2)
                pygame.draw.rect(fundo_surf,(95,58,18),(tx-5,ty+tr-5,10,20))
            for _ in range(100):
                fx=bx1+rng.randint(0,bx2-bx1); fy=by1+rng.randint(0,by2-by1)
                fc=choice([(218,78,78),(78,178,218),(218,218,58)])
                pygame.draw.circle(fundo_surf,fc,(fx,fy),4)

        elif bioma == "deserto":
            for _ in range(60):
                cx2=bx1+rng.randint(60,bx2-bx1-60); cy2=by1+rng.randint(60,by2-by1-60)
                pygame.draw.rect(fundo_surf,(58,138,38),(cx2-5,cy2-35,10,45))
                pygame.draw.rect(fundo_surf,(58,138,38),(cx2-22,cy2-18,16,8))
                pygame.draw.rect(fundo_surf,(58,138,38),(cx2+6, cy2-24,16,8))
            for _ in range(90):
                px=bx1+rng.randint(0,bx2-bx1); py=by1+rng.randint(0,by2-by1)
                pygame.draw.circle(fundo_surf,(168,138,88),(px,py),rng.randint(5,20))

        elif bioma == "neve":
            for _ in range(200):
                fx=bx1+rng.randint(0,bx2-bx1); fy=by1+rng.randint(0,by2-by1)
                pygame.draw.circle(fundo_surf,(255,255,255),(fx,fy),rng.randint(2,7))
            for _ in range(20):
                mx2=bx1+rng.randint(100,bx2-bx1-100)
                my2=by1+rng.randint(100,by2-by1-100)
                mh2=rng.randint(70,150)
                pts=[(mx2-mh2,my2+mh2//2),(mx2,my2-mh2),(mx2+mh2,my2+mh2//2)]
                pygame.draw.polygon(fundo_surf,(178,193,218),pts)
                pygame.draw.polygon(fundo_surf,(238,243,255),
                    [(mx2-18,my2-mh2+35),(mx2,my2-mh2),(mx2+18,my2-mh2+35)])

    # Bordas entre biomas (linhas visíveis)
    # Linha horizontal (meio Y)
    pygame.draw.rect(fundo_surf, C["borda"], (0, MEIO-6, MAPA_S, 12))
    # Linha vertical superior (meio X, apenas metade superior)
    pygame.draw.rect(fundo_surf, C["borda"], (MEIO-6, 0, 12, MEIO))

    # Marcadores de bioma
    try:
        f = pygame.font.SysFont("arial",48,bold=True)
        for bioma,(bx1,by1,bx2,by2) in BIOMAS_LAYOUT.items():
            cx2=(bx1+bx2)//2; cy2=(by1+by2)//2
            nomes_pt={"floresta":"FLORESTA","deserto":"DESERTO","neve":"NEVE"}
            t2=f.render(nomes_pt[bioma],True,(255,255,255,60))
            t2.set_alpha(35)
            fundo_surf.blit(t2,(cx2-t2.get_width()//2,cy2-24))
    except:
        pass

# ══════════════════════════════════════════════
#  PARTICULAS
# ══════════════════════════════════════════════
def spawn_parts(partics, n, x, y, cor, vel=3, vida=40):
    for _ in range(n):
        a = random.random()*math.pi*2
        v = vel*0.4 + random.random()*vel*0.6
        partics.append({"x":x,"y":y,"vx":math.cos(a)*v,"vy":math.sin(a)*v,
                        "cor":cor,"vida":vida,"vidaMax":vida,"r":rndI(2,5)})

# ══════════════════════════════════════════════
#  DESENHO: COMIDA
# ══════════════════════════════════════════════
def draw_comida(surf, c, tick, cam):
    sx,sy = cam.t(c["x"],c["y"])
    sy += math.sin(tick*.07+c["fase"])*3
    r = 10; cx2,cy2=int(sx),int(sy)
    if c["tipo"]=="fruta":
        pygame.draw.circle(surf,(38,198,38),(cx2,cy2),r)
        pygame.draw.circle(surf,(18,138,18),(cx2,cy2),r,2)
        pygame.draw.line(surf,(58,108,28),(cx2,cy2-r),(cx2+3,cy2-r-6),2)
    elif c["tipo"]=="cogumelo":
        pygame.draw.ellipse(surf,(168,58,198),(cx2-r,cy2-r,r*2,int(r*1.2)))
        pygame.draw.rect(surf,(208,188,188),(cx2-4,cy2,8,r-2))
        for dx2,dy2 in [(-4,-5),(3,-7),(0,-3)]:
            pygame.draw.circle(surf,(255,255,255),(cx2+dx2,cy2+dy2),2)
    else:
        pygame.draw.circle(surf,(198,58,38),(cx2,cy2),r)
        pygame.draw.circle(surf,(138,28,18),(cx2,cy2),r,2)
        pygame.draw.line(surf,(238,218,198),(cx2-5,cy2-5),(cx2+5,cy2+5),2)
        pygame.draw.line(surf,(238,218,198),(cx2+5,cy2-5),(cx2-5,cy2+5),2)

# ══════════════════════════════════════════════
#  DESENHO: ANIMAL
#  Tamanho = INTIMIDACAO (não impede ataque)
#  Quanto maior, mais vida/dano/xp mas FOGE mais fácil
# ══════════════════════════════════════════════
def draw_animal(surf, a, tick, cam):
    if not a["vivo"]: return
    sx,sy=cam.t(a["x"],a["y"])
    if not(-80<sx<SW+80 and -80<sy<SH+80): return
    cx,cy=int(sx),int(sy); r=a["raio"]; t=a["tl"]
    cor=a["cor"]; cor2=a["cor2"]

    # sombra no chão
    s_surf=pygame.Surface((r*2,r//2),pygame.SRCALPHA)
    pygame.draw.ellipse(s_surf,(0,0,0,60),(0,0,r*2,r//2))
    surf.blit(s_surf,(cx-r,cy+r-4))

    # cauda
    if a.get("cauda"):
        ac=a["ang"]+math.pi+math.sin(t*.1)*.4
        pygame.draw.line(surf,cor,(cx,cy),(cx+int(math.cos(ac)*(r+8)),cy+int(math.sin(ac)*(r+8))),max(2,r//5))

    # serpente
    if a.get("serpente"):
        for i in range(8,0,-1):
            wave=math.sin(t*.12+i*.7)*.3
            sa=a["ang"]+math.pi+wave
            d2=i*r*.55
            pygame.draw.circle(surf,ipc(cor,cor2,i/8),(cx+int(math.cos(sa)*d2),cy+int(math.sin(sa)*d2)),max(2,r-i*2))

    # corpo por tipo
    if a["tipo"]=="pinguim":
        pygame.draw.ellipse(surf,cor,(cx-r//2,cy-r,r,r*2))
        pygame.draw.ellipse(surf,cor2,(cx-r//3,cy-r//2,r//1.5,r))
        pygame.draw.circle(surf,(238,178,18),(cx,cy+r-5),max(3,r//4))
    elif a.get("gordo"):
        pygame.draw.ellipse(surf,cor,(cx-r,cy-r//2,r*2,r))
        pygame.draw.ellipse(surf,cor2,(cx-r//2,cy-r//3,r,r//2))
    elif a.get("juba"):
        pygame.draw.circle(surf,ipc(cor,(158,98,13),.5),(cx,cy),int(r*1.35))
        pygame.draw.circle(surf,cor,(cx,cy),r)
        pygame.draw.circle(surf,cor2,(cx,cy-r//4),r//2)
    else:
        pygame.draw.ellipse(surf,cor,(cx-r,cy-int(r*.75),r*2,int(r*1.5)))
        pygame.draw.circle(surf,cor2,(cx,cy-r//4),int(r*.55))

    # listras
    if a.get("listras"):
        for i in range(3):
            lx=cx-r//2+i*(r//2)
            pygame.draw.line(surf,(18,18,18),(lx,cy-r//2),(lx,cy+r//2),2)
    # manchas
    if a.get("manchas"):
        for i in range(4):
            am=i*math.pi/2
            pygame.draw.circle(surf,(58,38,18),(cx+int(math.cos(am)*r//2),cy+int(math.sin(am)*r//2)),4)
    # armadura
    if a.get("armadura"):
        pygame.draw.arc(surf,ipc(cor,(98,78,48),.5),(cx-r,cy-r//2,r*2,r),0,math.pi,3)
    # asas abelha
    if a.get("asas"):
        bat=math.sin(t*.3)*10
        for lado in(-1,1):
            s2=pygame.Surface((r,r//2),pygame.SRCALPHA)
            pygame.draw.ellipse(s2,(198,228,255,140),(0,0,r,r//2))
            surf.blit(s2,(cx+lado*(r-6),cy-r-int(bat)))

    # olhos
    if a["tipo"] not in ("cobra","foca"):
        for lado in(-1,1):
            ex=cx+lado*int(r*.33); ey=cy-int(r*.22)
            pygame.draw.circle(surf,(253,248,218),(ex,ey),max(2,r//4))
            pygame.draw.circle(surf,(13,13,13),(ex+lado,ey+1),max(1,r//8))

    # indicador de intimidação (tamanho = medo)
    # Aura de "ameaça" para animais grandes
    if r > 28:
        aura_s=pygame.Surface((r*2+20,r*2+20),pygame.SRCALPHA)
        intensidade=min(80,int((r-28)*2))
        pygame.draw.circle(aura_s,(255,50,50,intensidade),(r+10,r+10),r+10)
        surf.blit(aura_s,(cx-r-10,cy-r-10))

    # barra de vida
    if a["vida"]<a["vidaMax"]:
        bx2=cx-r; by2=cy-r-12; bw2=r*2
        pygame.draw.rect(surf,(48,8,8),(bx2,by2,bw2,6))
        pygame.draw.rect(surf,(198,38,38),(bx2,by2,int(bw2*a["vida"]/a["vidaMax"]),6))

    # XP que vai dar (mostrado no hover/proximidade)
    if r > 20:
        xp_txt_s = pygame.font.SysFont("arial",10).render(f"+{a['xpDrop']}xp",True,(255,220,80))
        surf.blit(xp_txt_s,(cx-xp_txt_s.get_width()//2,cy-r-22))

# ══════════════════════════════════════════════
#  DESENHO: JOGADOR
# ══════════════════════════════════════════════
def draw_jogador(surf, j, cam, fontp):
    if not j["vivo"]: return
    if j["invencivel"]>0 and (j["invencivel"]//5)%2==0: return
    sx,sy=cam.t(j["x"],j["y"])
    cx,cy=int(sx),int(sy); r=j["raio"]; t=j["tick"]
    nomes=[e["nome"] for e in j["evos"]]

    cor=C["player"]
    if "Carcinizacao" in nomes or "Omega Caranguejo" in nomes: cor=(208,53,13)
    elif "Aura de Fogo" in nomes:     cor=(218,88,18)
    elif "Ferrao Venenoso" in nomes:  cor=(78,198,48)
    elif "Camuflagem" in nomes:       cor=(68,138,53)
    elif "Instinto Predador" in nomes:cor=(178,28,28)
    cor2=ipc(cor,(255,255,255),.35)

    # sombra
    s_surf=pygame.Surface((r*2+4,r//2+2),pygame.SRCALPHA)
    pygame.draw.ellipse(s_surf,(0,0,0,70),(0,0,r*2+4,r//2+2))
    surf.blit(s_surf,(cx-r-2,cy+r-4))

    # aura fogo
    if j.get("auraFogo"):
        for i in range(3):
            ar=r+8+i*6+int(math.sin(t*.15+i)*4)
            s2=pygame.Surface((ar*2,ar*2),pygame.SRCALPHA)
            pygame.draw.circle(s2,(255,98,18,22),(ar,ar),ar)
            surf.blit(s2,(cx-ar,cy-ar))

    # aura veneno
    if j.get("auraVeneno"):
        av=r+16+int(math.sin(t*.1)*5)
        s2=pygame.Surface((av*2,av*2),pygame.SRCALPHA)
        pygame.draw.circle(s2,(78,218,38,30),(av,av),av)
        surf.blit(s2,(cx-av,cy-av))

    # asas
    if "Asas" in nomes or "Propulsao" in nomes:
        bat=math.sin(t*.2)*22
        for lado in(-1,1):
            pts=[(cx,cy-r//2),(cx+lado*(r+int(bat)),cy-r-18),(cx+lado*(r+10),cy+5)]
            pygame.draw.polygon(surf,(158,98,198),pts)

    # patas
    tem_patas=any(n in nomes for n in ["Patas Ageis","Carcinizacao","Dash","Pincas","Instinto Predador"])
    if tem_patas:
        for i in range(3):
            for lado in(-1,1):
                ba=lado*(30+i*28)*math.pi/180
                osc=math.sin(t*.14+i)*12*lado
                ar=ba+osc*math.pi/180+math.pi/2
                ox=cx+lado*int(r*.6); oy=cy+(i-1)*int(r*.42)
                pygame.draw.line(surf,cor2,(ox,oy),(ox+int(math.cos(ar)*r*.95),oy+int(math.sin(ar)*r*.95)),max(2,r//6))

    # espinhos
    if j.get("espinhos"):
        for k in range(8):
            ar=k*45*math.pi/180+t*.025
            pygame.draw.line(surf,(158,228,58),(cx+int(math.cos(ar)*r),cy+int(math.sin(ar)*r)),(cx+int(math.cos(ar)*(r+12)),cy+int(math.sin(ar)*(r+12))),2)

    # dash trail
    if j.get("dashVel",0)>2:
        for i in range(1,5):
            tx2=cx-int(math.cos(j["dashAng"])*i*8)
            ty2=cy-int(math.sin(j["dashAng"])*i*8)
            s2=pygame.Surface((r*2,r*2),pygame.SRCALPHA)
            pygame.draw.circle(s2,(*cor,48-i*10),(r,r),max(2,r-i*2))
            surf.blit(s2,(tx2-r,ty2-r))

    # corpo
    pygame.draw.circle(surf,cor,(cx,cy),r)
    pygame.draw.circle(surf,cor2,(cx,cy-r//4),int(r*.62))
    pygame.draw.circle(surf,(0,0,0),(cx,cy),r,2)

    # garras
    tem_garras=any(n in nomes for n in ["Garras Afiadas","Pincas","Mandibulas","Carcinizacao","Instinto Predador"])
    if tem_garras:
        for lado in(-1,1):
            gx=cx+lado*(r+10); gy=cy-4
            ab=int(math.sin(t*.1)*7)*lado
            pygame.draw.circle(surf,cor,(gx,gy),r//2)
            pygame.draw.line(surf,cor2,(gx,gy-4),(gx+lado*10,gy-12-ab),max(2,r//5))
            pygame.draw.line(surf,cor2,(gx,gy+2),(gx+lado*10,gy+8+ab),max(2,r//5))

    # ferrão
    if j.get("veneno"):
        pygame.draw.polygon(surf,(58,208,28),[(cx,cy-r-1),(cx-5,cy-r-15),(cx+5,cy-r-15)])

    # nadadeiras
    if "Nadadeiras" in nomes:
        for lado in(-1,1):
            ond=int(math.sin(t*.17)*7)*lado
            pygame.draw.polygon(surf,cor2,[(cx,cy),(cx+lado*(r+5),cy-9+ond),(cx+lado*(r+5),cy+9+ond)])

    # olhos
    for lado in(-1,1):
        ex=cx+lado*int(r*.35); ey=cy-int(r*.28)
        pygame.draw.circle(surf,(253,248,198),(ex,ey),max(3,r//4))
        pc=(198,0,0) if "Instinto Predador" in nomes else (13,13,13)
        pygame.draw.circle(surf,pc,(ex+lado,ey+1),max(1,r//7))

    # nome do jogador acima
    nt=fontp.render(j["nome"],True,(255,255,200))
    surf.blit(nt,(cx-nt.get_width()//2,cy-r-18))

# ══════════════════════════════════════════════
#  DESENHO: BOSS
# ══════════════════════════════════════════════
def draw_boss(surf, b, cam):
    if not b["vivo"]: return
    sx,sy=cam.t(b["x"],b["y"])
    if not(-150<sx<SW+150 and -150<sy<SH+150): return
    cx,cy=int(sx),int(sy); r=b["raio"]; t=b["tick"]
    cor=b["cor"]; cor2=b["cor2"]

    # sombra
    s_surf=pygame.Surface((r*3,r//2+4),pygame.SRCALPHA)
    pygame.draw.ellipse(s_surf,(0,0,0,80),(0,0,r*3,r//2+4))
    surf.blit(s_surf,(cx-r-r//2,cy+r-5))

    # aura pulsante
    ar2=r+20+int(math.sin(t*.07)*9)
    ac=cor2 if b["fase"]==1 else (255,78,18)
    s2=pygame.Surface((ar2*2,ar2*2),pygame.SRCALPHA)
    pygame.draw.circle(s2,(*ac,42),(ar2,ar2),ar2)
    surf.blit(s2,(cx-ar2,cy-ar2))

    # tentáculos
    for i in range(6):
        ba=i*(math.pi/3)+t*.02
        for seg in range(4):
            r1=(seg+1)*(r//4); r2=(seg+2)*(r//4)
            wave=math.sin(t*.08+i+seg*.5)*.35
            pygame.draw.line(surf,ipc(cor,(0,0,0),.35),
                (cx+int(math.cos(ba+wave)*r1),cy+int(math.sin(ba+wave)*r1)),
                (cx+int(math.cos(ba+wave)*r2),cy+int(math.sin(ba+wave)*r2)),3)

    # partes especiais
    for parte in b.get("partes_visuais",[]):
        if parte=="juba":
            pygame.draw.circle(surf,ipc(cor,(178,118,8),.5),(cx,cy),int(r*1.35),5)
        elif parte=="chifre":
            pygame.draw.polygon(surf,(218,198,148),[(cx,cy-r-5),(cx-7,cy-r-24),(cx+7,cy-r-24)])
        elif parte=="cauda_longa":
            ac2=b["ang"]+math.pi+math.sin(t*.08)*.5
            for seg in range(6):
                d2=(seg+1)*(r*.42)
                pygame.draw.circle(surf,ipc(cor,(78,78,78),seg/6),
                    (cx+int(math.cos(ac2)*d2),cy+int(math.sin(ac2)*d2)),max(3,r//2-seg*3))
        elif parte=="asas_boss":
            bat=math.sin(t*.15)*30
            for lado in(-1,1):
                pygame.draw.polygon(surf,ipc(cor,(0,0,0),.42),
                    [(cx,cy),(cx+lado*(r+int(bat)),cy-r-28),(cx+lado*(r+18),cy+12)])
        elif parte=="listras_boss":
            for i in range(5):
                lx=cx-r+i*(r//2)
                pygame.draw.line(surf,ipc(cor,(0,0,0),.6),(lx,cy-r),(lx,cy+r),3)
        elif parte=="manchas_boss":
            for i in range(6):
                am=i*math.pi/3
                pygame.draw.circle(surf,ipc(cor,(0,0,0),.5),(cx+int(math.cos(am)*r*.6),cy+int(math.sin(am)*r*.6)),5)
        elif parte=="pincas_boss":
            for lado in(-1,1):
                gx=cx+lado*(r+14); gy=cy-6
                ab=int(math.sin(t*.1)*10)*lado
                pygame.draw.circle(surf,cor,(gx,gy),r//2+4)
                pygame.draw.line(surf,cor2,(gx,gy-5),(gx+lado*14,gy-16-ab),4)
                pygame.draw.line(surf,cor2,(gx,gy+3),(gx+lado*14,gy+12+ab),4)
        elif parte=="serpente_boss":
            for i in range(10,0,-1):
                sa=b["ang"]+math.pi+math.sin(t*.1+i*.6)*.3
                d2=i*r*.5
                pygame.draw.circle(surf,ipc(cor,cor2,i/10),
                    (cx+int(math.cos(sa)*d2),cy+int(math.sin(sa)*d2)),max(3,r//2-i*2))
        elif parte in("gordo_boss","grande_boss","armadura_boss","concha_boss"):
            pygame.draw.circle(surf,ipc(cor,(255,255,255),.1),(cx,cy),int(r*1.15),3)

    # corpo
    bcor=cor if b["fase"]==1 else ipc(cor,(255,48,48),.38)
    pygame.draw.circle(surf,bcor,(cx,cy),r)
    pygame.draw.circle(surf,cor2,(cx,cy-r//4),int(r*.65))
    pygame.draw.circle(surf,(0,0,0),(cx,cy),r,2)

    # olhos furiosos
    for lado in(-1,1):
        ex=cx+lado*int(r*.38); ey=cy-int(r*.2)
        pygame.draw.circle(surf,(253,28,28),(ex,ey),max(4,r//3))
        pygame.draw.circle(surf,(0,0,0),(ex,ey),max(2,r//6))

    # espinhos fase 2
    if b["fase"]==2:
        for k in range(12):
            ar3=k*30*math.pi/180+t*.035
            pygame.draw.line(surf,(253,68,8),
                (cx+int(math.cos(ar3)*r),cy+int(math.sin(ar3)*r)),
                (cx+int(math.cos(ar3)*(r+18)),cy+int(math.sin(ar3)*(r+18))),3)

    # projéteis
    for p in b.get("projeteis",[]):
        psx,psy=cam.t(p["x"],p["y"])
        for i in range(1,4):
            tx=int(psx-math.cos(p["ang"])*i*5); ty=int(psy-math.sin(p["ang"])*i*5)
            s2=pygame.Surface((p["r"]*2,p["r"]*2),pygame.SRCALPHA)
            pygame.draw.circle(s2,(*cor,68-i*18),(p["r"],p["r"]),p["r"]-i)
            surf.blit(s2,(tx-p["r"],ty-p["r"]))
        pygame.draw.circle(surf,cor,(int(psx),int(psy)),p["r"])

# ══════════════════════════════════════════════
#  HUD
# ══════════════════════════════════════════════
def draw_bar(surf,x,y,w,h,val,maxi,cor,bg=(38,38,38),rad=5):
    pygame.draw.rect(surf,bg,(x,y,w,h),border_radius=rad)
    fw=max(0,int(w*clamp(val,0,maxi)/max(1,maxi)))
    if fw>0: pygame.draw.rect(surf,cor,(x,y,fw,h),border_radius=rad)
    pygame.draw.rect(surf,ipc(cor,(255,255,255),.22),(x,y,w,h),2,border_radius=rad)

def draw_hud(surf, j, cam, tick, elapsed, boss, fn, fp, bioma_atual, boss_fila_idx):
    hbg=pygame.Surface((SW,58),pygame.SRCALPHA); hbg.fill((0,0,0,138)); surf.blit(hbg,(0,0))

    # Vida
    draw_bar(surf,12,10,205,18,j["vida"],j["vidaMax"],(188,38,38),(38,8,8))
    surf.blit(fp.render(f"HP {int(j['vida'])}/{j['vidaMax']}",True,C["texto"]),(18,12))
    # XP
    draw_bar(surf,12,33,205,12,j["xp"],j["xpProx"],(48,188,68),(13,33,13))
    surf.blit(fp.render(f"XP {j['xp']}/{j['xpProx']}",True,C["texto"]),(18,34))

    # Nivel
    surf.blit(fn.render(f"Nv{j['nivel']}",True,C["ouro"]),(225,10))

    # Bioma
    bcors={"floresta":(38,158,38),"deserto":(198,148,38),"neve":(118,158,218)}
    bc=bcors.get(bioma_atual,(148,148,148))
    bt=fn.render(f"[{bioma_atual.upper()}]",True,bc)
    surf.blit(bt,(SW//2-bt.get_width()//2,10))

    # Timer
    rem=max(0,DURACAO-elapsed)
    m=int(rem)//60; s=int(rem)%60
    ctim=C["aviso"] if rem<30 else C["texto"]
    tt=fn.render(f"{m}:{s:02d}",True,ctim)
    surf.blit(tt,(SW//2-tt.get_width()//2,30))

    # Próximo boss
    surf.blit(fp.render(f"Proximo boss: {POOL_BOSSES[boss_fila_idx%len(POOL_BOSSES)]['nome']}",True,(188,108,108)),(SW//2+80,30))

    # Boss HP
    if boss and boss["vivo"]:
        bw=400; bx2=SW//2-bw//2; by2=SH-52
        bn=fn.render(f"BOSS: {boss['nome']} | Fase {boss['fase']}",True,(255,108,108))
        surf.blit(bn,(SW//2-bn.get_width()//2,by2-20))
        draw_bar(surf,bx2,by2,bw,20,boss["vida"],boss["vidaMax"],(178,18,18),(48,4,4),8)
        bvt=fp.render(f"{int(boss['vida'])}/{boss['vidaMax']}",True,(255,198,198))
        surf.blit(bvt,(SW//2-bvt.get_width()//2,by2+2))

    # Evoluções
    ex=SW-10; ey=10
    surf.blit(fp.render("Evos:",True,(158,158,158)),(ex-fp.size("Evos:")[0],ey)); ey+=15
    for evo in j["evos"][-8:]:
        cc=[(158,158,158),(78,148,218),(168,68,218)][evo["rar"]-1]
        te=fp.render(f"{evo['ic']} {evo['nome']}",True,cc)
        surf.blit(te,(ex-te.get_width(),ey)); ey+=14

    # Hint
    hint="WASD=mover"+(" Shift=Dash" if j.get("dash") else "")+" ESC=pause"
    ht=fp.render(hint,True,(98,118,88))
    surf.blit(ht,(SW//2-ht.get_width()//2,SH-16))

    # Mini-mapa
    draw_minimap(surf,j,cam,boss)

def draw_minimap(surf, j, cam, boss):
    mw,mh=160,160; mx=SW-mw-10; my=SH-mh-24
    ms=pygame.Surface((mw,mh),pygame.SRCALPHA)
    ms.fill((0,0,0,158))
    # biomas no mini-mapa quadrado
    for bioma,(bx1,by1,bx2,by2) in BIOMAS_LAYOUT.items():
        bcol={"floresta":(28,78,18),"deserto":(158,118,48),"neve":(158,178,208)}[bioma]
        pbx=int(bx1/MAPA_S*mw); pby=int(by1/MAPA_S*mh)
        pbw=int((bx2-bx1)/MAPA_S*mw); pbh=int((by2-by1)/MAPA_S*mh)
        pygame.draw.rect(ms,(*bcol,118),(pbx,pby,pbw,pbh))
    # bordas
    pygame.draw.line(ms,(98,78,38),(mw//2,0),(mw//2,mh//2),1)
    pygame.draw.line(ms,(98,78,38),(0,mh//2),(mw,mh//2),1)
    # jogador
    jmx=int(j["x"]/MAPA_S*mw); jmy=int(j["y"]/MAPA_S*mh)
    pygame.draw.circle(ms,(78,138,255),(jmx,jmy),4)
    # boss
    if boss and boss["vivo"]:
        bmx=int(boss["x"]/MAPA_S*mw); bmy=int(boss["y"]/MAPA_S*mh)
        pygame.draw.circle(ms,(218,28,28),(bmx,bmy),5)
    pygame.draw.rect(ms,(98,128,98),(0,0,mw,mh),1)
    surf.blit(ms,(mx,my))

# ══════════════════════════════════════════════
#  TELA DE LOGIN
# ══════════════════════════════════════════════
async def tela_login(surf, clock, fn, fp, ft):
    nome=""; senha=""; campo="nome"; tick=0; erro=""
    while True:
        for ev in pygame.event.get():
            if ev.type==pygame.QUIT: pygame.quit(); sys.exit()
            if ev.type==pygame.KEYDOWN:
                if ev.key==pygame.K_TAB: campo="senha" if campo=="nome" else "nome"
                elif ev.key==pygame.K_BACKSPACE:
                    if campo=="nome": nome=nome[:-1]
                    else: senha=senha[:-1]
                elif ev.key==pygame.K_RETURN:
                    if not nome.strip(): erro="Digite seu nome!"
                    elif len(senha)<3: erro="Senha muito curta (min 3)!"
                    else: return nome.strip(),senha
                else:
                    ch=ev.unicode
                    if ch and ch.isprintable():
                        if campo=="nome" and len(nome)<16: nome+=ch
                        elif campo=="senha" and len(senha)<16: senha+=ch
            if ev.type==pygame.MOUSEBUTTONDOWN:
                mx2,my2=ev.pos
                if 348<=mx2<=610:
                    if 253<=my2<=283: campo="nome"
                    elif 313<=my2<=343: campo="senha"
                bx3=SW//2-80; by3=390
                if bx3<=mx2<=bx3+160 and by3<=my2<=by3+40:
                    if not nome.strip(): erro="Digite seu nome!"
                    elif len(senha)<3: erro="Senha muito curta!"
                    else: return nome.strip(),senha
        tick+=1
        surf.fill((16,26,10))
        tit=ft.render("EVERYTHING IS CRAB",True,C["ouro"])
        surf.blit(tit,(SW//2-tit.get_width()//2,70))
        sub=fn.render("Roguelite - Mapa Quadrado - 3 Biomas - Bosses Rotativos",True,(138,178,98))
        surf.blit(sub,(SW//2-sub.get_width()//2,108))
        # caranguejo animado
        ccx,ccy=SW//2,188; cr=28+int(math.sin(tick*.05)*4)
        pygame.draw.circle(surf,(208,58,18),(ccx,ccy),cr)
        pygame.draw.circle(surf,(238,98,48),(ccx,ccy-cr//4),int(cr*.62))
        for lado in(-1,1):
            gx=ccx+lado*(cr+10); gy=ccy-4; ab=int(math.sin(tick*.08)*8)*lado
            pygame.draw.circle(surf,(208,58,18),(gx,gy),cr//2)
            pygame.draw.line(surf,(238,98,48),(gx,gy-4),(gx+lado*12,gy-14-ab),3)
            pygame.draw.line(surf,(238,98,48),(gx,gy+2),(gx+lado*12,gy+10+ab),3)
        for lado in(-1,1):
            ex=ccx+lado*int(cr*.38); ey=ccy-int(cr*.28)
            pygame.draw.circle(surf,(253,248,198),(ex,ey),max(3,cr//4))
            pygame.draw.circle(surf,(13,13,13),(ex+lado,ey+1),max(1,cr//7))
        # inputs
        for i,(label,val,cp) in enumerate([("Nome:",nome,"nome"),("Senha:","*"*len(senha),"senha")]):
            bx2=348; by2=248+i*60; bw2=262; bh2=30
            ativo=(campo==cp)
            cor_b=C["ouro"] if ativo else (78,98,58)
            surf.blit(fn.render(label,True,C["texto"]),(bx2,by2-20))
            pygame.draw.rect(surf,(18,33,13),(bx2,by2,bw2,bh2),border_radius=6)
            pygame.draw.rect(surf,cor_b,(bx2,by2,bw2,bh2),2,border_radius=6)
            vt=fn.render(val+("|" if ativo and tick//30%2==0 else ""),True,C["texto"])
            surf.blit(vt,(bx2+8,by2+5))
        # botao
        bx3=SW//2-80; by3=388
        pygame.draw.rect(surf,(28,118,38),(bx3,by3,160,40),border_radius=10)
        pygame.draw.rect(surf,(48,178,58),(bx3,by3,160,40),2,border_radius=10)
        pt=fn.render("[ JOGAR ]",True,(198,238,178))
        surf.blit(pt,(bx3+80-pt.get_width()//2,by3+10))
        if erro:
            surf.blit(fn.render(erro,True,(218,58,58)),(SW//2-fn.size(erro)[0]//2,443))
        # biomas info
        for i,(b_nome,b_cor,b_anims) in enumerate([
            ("FLORESTA",(38,158,38),"Abelha, Esquilo, Caracol, Lobo, Raposa Laranja"),
            ("DESERTO", (198,148,38),"Cobra, Tatu, Zebra, Leao, Raposa Aridez"),
            ("NEVE",    (118,158,218),"Pinguim, Leopardo, Foca, Urso Polar, Raposa Branca"),
        ]):
            surf.blit(fp.render(f"  {b_nome}: {b_anims}",True,b_cor),(SW//2-350,490+i*18))
        pygame.display.flip(); clock.tick(FPS)
        await asyncio.sleep(0)

# ══════════════════════════════════════════════
#  TELA DE EVOLUÇÃO
# ══════════════════════════════════════════════
async def tela_evolucao(surf, clock, ft, fn, fp, boss_evo=False):
    opcoes=random.sample(EVOLUCOES_BOSS,min(3,len(EVOLUCOES_BOSS))) if boss_evo else escolher_evos(3)
    cw,ch=218,285; gap=24
    total=cw*3+gap*2; cx_ini=(SW-total)//2; cy_ini=(SH-ch)//2
    sel=None; hover=-1; tick=0
    while sel is None:
        for ev in pygame.event.get():
            if ev.type==pygame.QUIT: pygame.quit(); sys.exit()
            if ev.type==pygame.KEYDOWN:
                if ev.key==pygame.K_1: sel=0
                elif ev.key==pygame.K_2: sel=1
                elif ev.key==pygame.K_3: sel=2
            if ev.type==pygame.MOUSEBUTTONDOWN and ev.button==1:
                mx2,my2=ev.pos
                for i in range(3):
                    ccx=cx_ini+i*(cw+gap)
                    if ccx<=mx2<=ccx+cw and cy_ini<=my2<=cy_ini+ch: sel=i
        mx2,my2=pygame.mouse.get_pos(); hover=-1
        for i in range(3):
            ccx=cx_ini+i*(cw+gap)
            if ccx<=mx2<=ccx+cw and cy_ini<=my2<=cy_ini+ch: hover=i
        tick+=1
        ov=pygame.Surface((SW,SH),pygame.SRCALPHA); ov.fill((0,0,0,182)); surf.blit(ov,(0,0))
        tit_txt="BOSS DERROTADO! Evolucao Epica:" if boss_evo else "EVOLUCAO! Escolha:"
        tit=ft.render(tit_txt,True,C["ouro"] if boss_evo else (253,218,68))
        surf.blit(tit,(SW//2-tit.get_width()//2,cy_ini-52))
        surf.blit(fp.render("Clique ou tecle 1/2/3",True,(158,158,158)),(SW//2-fp.size("Clique ou tecle 1/2/3")[0]//2,cy_ini-24))
        for i,evo in enumerate(opcoes):
            ccx=cx_ini+i*(cw+gap); is_h=(i==hover)
            cy_c=cy_ini-(12 if is_h else 0); rar=evo["rar"]
            cor_card=(53,43,68) if rar==3 else ((48,63,78) if rar==2 else (43,56,43))
            cor_borda=(218,168,28) if rar==3 else ((78,158,218) if rar==2 else (88,158,88))
            if is_h: cor_borda=ipc(cor_borda,(255,255,255),.28)
            pygame.draw.rect(surf,cor_card,(ccx,cy_c,cw,ch),border_radius=13)
            pygame.draw.rect(surf,cor_borda,(ccx,cy_c,cw,ch),3,border_radius=13)
            rl=["","Comum","Rara","EPICA"][rar]
            surf.blit(fp.render(f"[{rl}][{i+1}]",True,cor_borda),(ccx+8,cy_c+8))
            ic_t=ft.render(evo["ic"],True,(253,253,218))
            surf.blit(ic_t,(ccx+cw//2-ic_t.get_width()//2,cy_c+34))
            nm=fn.render(evo["nome"],True,(253,226,88))
            surf.blit(nm,(ccx+cw//2-nm.get_width()//2,cy_c+106))
            pygame.draw.line(surf,cor_borda,(ccx+12,cy_c+130),(ccx+cw-12,cy_c+130),1)
            dc=fp.render(evo["desc"],True,(188,203,213))
            surf.blit(dc,(ccx+cw//2-dc.get_width()//2,cy_c+140))
            yb=cy_c+164
            for chv,lbl in [("vel","Vel"),("dano","Dano"),("vida","Vida"),("def","Def"),("regen","Regen")]:
                if chv in evo:
                    v=evo[chv]; sym="x" if isinstance(v,float) else "+"
                    bt=fp.render(f"{lbl}: {sym}{v}",True,(148,218,148))
                    surf.blit(bt,(ccx+cw//2-bt.get_width()//2,yb)); yb+=16
        pygame.display.flip(); clock.tick(FPS)
        await asyncio.sleep(0)
    return opcoes[sel if sel is not None and sel<len(opcoes) else 0]

# ══════════════════════════════════════════════
#  TELA FIM / PAUSE
# ══════════════════════════════════════════════
async def tela_fim(surf,clock,ft,fn,fp,ganhou,nome_j,nivel,elapsed,bosses,kills):
    tick=0
    while True:
        for ev in pygame.event.get():
            if ev.type==pygame.QUIT: return
            if ev.type in(pygame.KEYDOWN,pygame.MOUSEBUTTONDOWN): return
        tick+=1
        surf.fill((8,5,3) if not ganhou else (8,22,6))
        msg="VOCE SOBREVIVEU!" if ganhou else "VOCE FOI DEVORADO..."
        mc=(78,218,78) if ganhou else (208,58,38)
        tit=ft.render(msg,True,mc)
        surf.blit(tit,(SW//2-tit.get_width()//2,SH//2-108))
        for i,(linha,cor3) in enumerate([
            (f"Jogador: {nome_j}",(198,198,198)),
            (f"Nivel: {nivel}",(253,218,98)),
            (f"Tempo: {int(elapsed)}s",(198,198,198)),
            (f"Bosses: {bosses}",(198,98,218)),
            (f"Animais: {kills}",(218,138,78)),
        ]):
            t2=fn.render(linha,True,cor3)
            surf.blit(t2,(SW//2-t2.get_width()//2,SH//2-18+i*34))
        h=fp.render("[ Qualquer tecla ]",True,(108,108,108))
        surf.blit(h,(SW//2-h.get_width()//2,SH//2+168))
        pygame.display.flip(); clock.tick(FPS)
        await asyncio.sleep(0)

async def tela_pause(surf,clock,ft,fn,fp,j,elapsed,bosses,kills,boss_fila_idx):
    while True:
        for ev in pygame.event.get():
            if ev.type==pygame.QUIT: pygame.quit(); sys.exit()
            if ev.type==pygame.KEYDOWN:
                if ev.key in(pygame.K_ESCAPE,pygame.K_p,pygame.K_RETURN): return "resume"
                if ev.key==pygame.K_r: return "restart"
            if ev.type==pygame.MOUSEBUTTONDOWN:
                mx2,my2=ev.pos
                if SW//2-125<=mx2<=SW//2-5 and SH-110<=my2<=SH-75: return "resume"
                if SW//2+5<=mx2<=SW//2+125  and SH-110<=my2<=SH-75: return "restart"
        ov=pygame.Surface((SW,SH),pygame.SRCALPHA); ov.fill((0,0,0,198)); surf.blit(ov,(0,0))
        surf.blit(ft.render("PAUSADO",True,C["texto"]),(SW//2-ft.size("PAUSADO")[0]//2,55))
        rem=max(0,DURACAO-elapsed)
        stats=[
            ("Jogador",j["nome"]),("Nivel",str(j["nivel"])),
            (f"HP",f"{int(j['vida'])}/{j['vidaMax']}"),
            ("Vel",f"x{j['mVel']:.2f}"),("Dano",f"x{j['mDano']:.2f}"),
            ("Def",f"-{int((1-j['mDef'])*100)}%"),("Regen",f"+{j['regenPs']}/s"),
            ("Bosses",str(bosses)),("Kills",str(kills)),
            ("Tempo",f"{int(rem//60)}:{int(rem%60):02d}"),
            ("Prox Boss",POOL_BOSSES[boss_fila_idx%len(POOL_BOSSES)]["nome"]),
        ]
        for i,(k,v) in enumerate(stats):
            col=0 if i<6 else 1; row=i%6
            x2=SW//2-285+col*290; y2=120+row*42
            pygame.draw.rect(surf,(18,28,13),(x2,y2,280,36),border_radius=6)
            surf.blit(fp.render(k,True,(128,148,108)),(x2+8,y2+10))
            vt=fn.render(v,True,C["ouro"])
            surf.blit(vt,(x2+280-vt.get_width()-8,y2+8))
        yt=388
        surf.blit(fn.render("Evolucoes obtidas:",True,(158,158,158)),(SW//2-118,yt)); yt+=24
        for evo in j["evos"]:
            cc=[(158,158,158),(78,148,218),(168,68,218)][evo["rar"]-1]
            et=fp.render(f"{evo['ic']} {evo['nome']} (Nv{evo.get('nivelobtido','?')})",True,cc)
            surf.blit(et,(SW//2-et.get_width()//2,yt)); yt+=15
            if yt>SH-118: break
        for bx3,lbl,cor3 in [(SW//2-125,"Continuar",(38,158,48)),(SW//2+5,"Reiniciar",(158,58,28))]:
            pygame.draw.rect(surf,cor3,(bx3,SH-110,120,36),border_radius=8)
            bt=fn.render(lbl,True,(238,238,238))
            surf.blit(bt,(bx3+60-bt.get_width()//2,SH-102))
        surf.blit(fp.render("ESC=continuar  R=reiniciar",True,(88,88,88)),(SW//2-fp.size("ESC=continuar  R=reiniciar")[0]//2,SH-58))
        pygame.display.flip(); clock.tick(FPS)
        await asyncio.sleep(0)

# ══════════════════════════════════════════════
#  HELPERS
# ══════════════════════════════════════════════
def novo_jogador(nome):
    return {
        "nome":nome,"x":float(MAPA_S*.08),"y":float(MAPA_S*.25),
        "raio":18,"raioBase":18,"vida":100,"vidaMax":100,
        "velBase":2.2,"mVel":1.0,"mDano":1.0,"mDef":1.0,"mXp":1.0,"mRaioCol":1.0,
        "dano":15,"nivel":1,"xp":0,"xpProx":60,
        "regenPs":0,"regenTick":0,
        "espinhos":False,"veneno":False,"camuflagem":False,
        "dash":False,"auraFogo":False,"auraVeneno":False,
        "invencivel":0,"atacando":0,"dashVel":0,"dashAng":0,"dashCd":0,
        "evos":[],"vivo":True,"tick":0,
    }

def aplicar_evo(j,e):
    j["evos"].append({**e,"nivelobtido":j["nivel"]})
    if "vel"        in e: j["mVel"]*=e["vel"]
    if "dano"       in e: j["mDano"]*=e["dano"]
    if "def"        in e: j["mDef"]*=e["def"]
    if "xpBonus"    in e: j["mXp"]*=e["xpBonus"]
    if "raioColeta" in e: j["mRaioCol"]*=e["raioColeta"]
    if "regen"      in e: j["regenPs"]+=e["regen"]
    if "espinhos"   in e: j["espinhos"]=True
    if "veneno"     in e: j["veneno"]=True
    if "camuflagem" in e: j["camuflagem"]=True
    if "dash"       in e: j["dash"]=True
    if "auraFogo"   in e: j["auraFogo"]=True
    if "auraVeneno" in e: j["auraVeneno"]=True
    if "vida"       in e: j["vidaMax"]+=e["vida"]; j["vida"]+=e["vida"]
    if "tamanho"    in e: j["raio"]=int(j["raioBase"]*e["tamanho"]); j["raioBase"]=j["raio"]
    j["nivel"]+=1

def ganhar_xp(j,qtd):
    j["xp"]+=int(qtd*j["mXp"])
    if j["xp"]>=j["xpProx"]:
        j["xp"]-=j["xpProx"]; j["xpProx"]=int(j["xpProx"]*1.32); return True
    return False

def hit_j(j,dano):
    if j["invencivel"]>0: return
    j["vida"]-=max(1,int(dano*j["mDef"])); j["invencivel"]=50
    if j["vida"]<=0: j["vida"]=0; j["vivo"]=False

def spawn_animal(bioma, nivel=1):
    bx1,by1,bx2,by2=BIOMAS_LAYOUT[bioma]
    dados=choice(ANIMAIS_BIOMA[bioma])
    # Tamanho baseado no nível — maior = mais intimidador, mais vida, mais XP
    # MAS não impede ataque: qualquer um pode atacar qualquer um
    r_base=12+nivel*5
    mult_r=1.4 if dados.get("grande") or dados.get("gordo") else 1.0
    r=int(r_base*mult_r)
    # XP escala com tamanho: animais grandes dão muito mais XP
    xp_drop=int((dados["xpBase"]+nivel*8) * (r/18))
    dano_drop=int((dados["danoBase"]+nivel*3) * (r/18))
    spd=rnd(0.55,1.35)*(0.6 if dados.get("lento") else (1.35 if dados.get("rapido") else 1.0))
    return {
        **dados,
        "x":float(rnd(bx1+50,bx2-50)),"y":float(rnd(by1+50,by2-50)),
        "raio":r,"vida":r*6,"vidaMax":r*6,
        "vel":spd,"nivel":nivel,"ang":random.random()*math.pi*2,
        "timerDir":rndI(30,80),"vivo":True,"tl":rndI(0,60),
        "xpDrop":xp_drop,"danoDrop":dano_drop,"bioma":bioma,
        # animais maiores fogem mais fácil (intimidados pelo jogador)
        "limiar_fuga": 0.9 if r>30 else (1.1 if r>20 else 1.3),
    }

def spawn_boss_da_fila(fila_idx, bioma_atual):
    # Garante que o mesmo boss só volta após 5 outros (fila circular)
    info=POOL_BOSSES[fila_idx % len(POOL_BOSSES)]
    b_bioma=info["bioma"]
    # Se o boss é de bioma específico, spawna nele; senão usa o atual
    if b_bioma=="todos": b_bioma=bioma_atual
    bx1,by1,bx2,by2=BIOMAS_LAYOUT[b_bioma]
    lado=rndI(0,3)
    if lado==0: bx3,by3=rnd(bx1+100,bx2-100),float(by1+90)
    elif lado==1: bx3,by3=rnd(bx1+100,bx2-100),float(by2-90)
    elif lado==2: bx3,by3=float(bx1+90),rnd(by1+100,by2-100)
    else: bx3,by3=float(bx2-90),rnd(by1+100,by2-100)
    vm=info["vm_base"]
    return {
        "x":bx3,"y":by3,"nome":info["nome"],
        "cor":info["cor"],"cor2":ipc(info["cor"],(255,255,255),.35),
        "raio":60,"vidaMax":vm,"vida":float(vm),
        "vel":1.05,"danoContato":35,"ang":0.0,
        "fase":1,"tick":0,"invencivel":0,
        "projTimr":0,"projeteis":[],"vivo":True,
        "partes_visuais":info["partes"],"bioma":b_bioma,
        "fila_idx":fila_idx,
    }

# ══════════════════════════════════════════════
#  MAIN
# ══════════════════════════════════════════════
async def main():
    pygame.init()
    surf=pygame.display.set_mode((SW,SH))
    pygame.display.set_caption("Everything is Crab")
    clock=pygame.time.Clock()
    try:
        ft=pygame.font.SysFont("arial",26,bold=True)
        fn=pygame.font.SysFont("arial",20)
        fp=pygame.font.SysFont("arial",14)
    except:
        ft=pygame.font.SysFont(None,28,bold=True)
        fn=pygame.font.SysFont(None,22)
        fp=pygame.font.SysFont(None,15)

    gerar_fundo()

    while True:
        nome_jogador,_=await tela_login(surf,clock,fn,fp,ft)
        j=novo_jogador(nome_jogador)
        cam=Camera(); cam.x=j["x"]-SW//2; cam.y=j["y"]-SH//2

        animais=[]; comidas=[]; boss=None; particulas=[]
        boss_fila_idx=0   # índice na fila rotativa de bosses
        boss_timer=BOSS_CADA*FPS
        boss_aviso=False
        bosses_mortos=0; kill_count=0; food_count=0
        tick=0; start_ms=pygame.time.get_ticks()
        t_comida=0; t_animal=0; keys={}

        # Spawn inicial
        for bioma in BIOMAS_LAYOUT:
            for _ in range(10):
                animais.append(spawn_animal(bioma,rndI(1,2)))
            bx1,by1,bx2,by2=BIOMAS_LAYOUT[bioma]
            for _ in range(14):
                tipo=choice(["fruta","fruta","cogumelo"])
                comidas.append({"x":rnd(bx1+30,bx2-30),"y":rnd(by1+30,by2-30),
                    "tipo":tipo,"raio":10,"fase":random.random()*math.pi*2,
                    "xp":{"fruta":8,"cogumelo":16}[tipo]})

        rodando=True; reiniciar=False

        while rodando:
            elapsed=(pygame.time.get_ticks()-start_ms)/1000.0
            bioma_atual=get_bioma(j["x"],j["y"])

            for ev in pygame.event.get():
                if ev.type==pygame.QUIT: pygame.quit(); sys.exit()
                if ev.type==pygame.KEYDOWN:
                    keys[ev.key]=True
                    if ev.key in(pygame.K_ESCAPE,pygame.K_p):
                        acao=await tela_pause(surf,clock,ft,fn,fp,j,elapsed,bosses_mortos,kill_count,boss_fila_idx)
                        if acao=="restart": rodando=False; reiniciar=True
                if ev.type==pygame.KEYUP: keys[ev.key]=False

            # ── Jogador ──────────────────────────────────────────
            j["tick"]+=1
            if j["invencivel"]>0: j["invencivel"]-=1
            if j["atacando"]>0:   j["atacando"]-=1
            if j["dashCd"]>0:     j["dashCd"]-=1
            dx,dy=0,0
            if keys.get(pygame.K_LEFT) or keys.get(pygame.K_a):  dx-=1
            if keys.get(pygame.K_RIGHT) or keys.get(pygame.K_d): dx+=1
            if keys.get(pygame.K_UP)   or keys.get(pygame.K_w):  dy-=1
            if keys.get(pygame.K_DOWN) or keys.get(pygame.K_s):  dy+=1
            if dx and dy: dx*=0.7071; dy*=0.7071
            vel=j["velBase"]*j["mVel"]
            if j["dash"] and (keys.get(pygame.K_LSHIFT) or keys.get(pygame.K_RSHIFT)) and j["dashCd"]==0 and (dx or dy):
                j["dashVel"]=14.0; j["dashAng"]=math.atan2(dy,dx)
                j["dashCd"]=60; j["invencivel"]=max(j["invencivel"],18)
            if j["dashVel"]>0:
                j["x"]+=math.cos(j["dashAng"])*j["dashVel"]
                j["y"]+=math.sin(j["dashAng"])*j["dashVel"]
                j["dashVel"]=max(0,j["dashVel"]-1.6)
            else:
                j["x"]+=dx*vel; j["y"]+=dy*vel
            j["x"]=clamp(j["x"],j["raio"],MAPA_S-j["raio"])
            j["y"]=clamp(j["y"],j["raio"],MAPA_S-j["raio"])
            if j["regenPs"]>0:
                j["regenTick"]+=1
                if j["regenTick"]>=FPS: j["regenTick"]=0; j["vida"]=min(j["vidaMax"],j["vida"]+j["regenPs"])
            cam.seguir(j["x"],j["y"])

            # ── Animais ──────────────────────────────────────────
            for a in animais:
                if not a["vivo"]: continue
                a["tl"]+=1
                dx2=j["x"]-a["x"]; dy2=j["y"]-a["y"]; d=math.hypot(dx2,dy2)
                perc=200*(0.5 if j.get("camuflagem") else 1.0)
                if d<perc:
                    # TAMANHO = INTIMIDAÇÃO: animais maiores fogem mais fácil
                    # limiar_fuga: quanto maior, mais difícil de assustar
                    if a["raio"]>j["raio"]*a["limiar_fuga"]:
                        a["ang"]=math.atan2(dy2,dx2)+rnd(-.15,.15)
                    else:
                        # menores fogem (mas podem ser atacados pelo jogador de qualquer tamanho)
                        a["ang"]=math.atan2(-dy2,-dx2)+rnd(-.25,.25)
                else:
                    a["timerDir"]-=1
                    if a["timerDir"]<=0: a["ang"]=random.random()*math.pi*2; a["timerDir"]=rndI(40,100)
                a["x"]+=math.cos(a["ang"])*a["vel"]; a["y"]+=math.sin(a["ang"])*a["vel"]
                a["x"]=clamp(a["x"],a["raio"],MAPA_S-a["raio"])
                a["y"]=clamp(a["y"],a["raio"],MAPA_S-a["raio"])

            # ── Boss ─────────────────────────────────────────────
            if boss and boss["vivo"]:
                boss["tick"]+=1
                if boss["invencivel"]>0: boss["invencivel"]-=1
                if boss["fase"]==1 and boss["vida"]<boss["vidaMax"]*.5:
                    boss["fase"]=2; boss["vel"]*=1.5; boss["danoContato"]=int(boss["danoContato"]*1.4)
                dx3=j["x"]-boss["x"]; dy3=j["y"]-boss["y"]
                boss["ang"]=math.atan2(dy3,dx3)+math.sin(boss["tick"]*.06)*.45
                boss["x"]+=math.cos(boss["ang"])*boss["vel"]
                boss["y"]+=math.sin(boss["ang"])*boss["vel"]
                boss["x"]=clamp(boss["x"],boss["raio"],MAPA_S-boss["raio"])
                boss["y"]=clamp(boss["y"],boss["raio"],MAPA_S-boss["raio"])
                if boss["fase"]==2:
                    boss["projTimr"]+=1
                    if boss["projTimr"]>=90:
                        boss["projTimr"]=0
                        for k in range(5):
                            a2=math.atan2(j["y"]-boss["y"],j["x"]-boss["x"])+math.radians(-40+k*20)
                            boss["projeteis"].append({"x":boss["x"],"y":boss["y"],"ang":a2,"vel":6,"r":9,"vivo":True,"tick":0})
                for p in boss["projeteis"]:
                    p["x"]+=math.cos(p["ang"])*p["vel"]; p["y"]+=math.sin(p["ang"])*p["vel"]
                    p["tick"]+=1
                    if p["tick"]>220 or not(0<p["x"]<MAPA_S and 0<p["y"]<MAPA_S): p["vivo"]=False
                boss["projeteis"]=[p for p in boss["projeteis"] if p["vivo"]]

            # ── Combate ──────────────────────────────────────────
            rcol=(j["raio"]+22)*j["mRaioCol"]

            # coleta comida
            novas=[]
            for c in comidas:
                if dist(j["x"],j["y"],c["x"],c["y"])<rcol:
                    food_count+=1
                    cor_p=(55,205,55) if c["tipo"]=="fruta" else (165,65,205)
                    spawn_parts(particulas,8,c["x"],c["y"],cor_p,2.5)
                    if ganhar_xp(j,c["xp"]):
                        evo=await tela_evolucao(surf,clock,ft,fn,fp)
                        aplicar_evo(j,evo)
                else:
                    novas.append(c)
            comidas=novas

            # combate animais — QUALQUER TAMANHO pode atacar qualquer um
            for a in animais:
                if not a["vivo"]: continue
                d2=dist(j["x"],j["y"],a["x"],a["y"])
                if d2<j["raio"]+a["raio"]-4:
                    # Jogador SEMPRE pode atacar, independente do tamanho
                    if j["atacando"]==0:
                        dano_infligido=j["dano"]*j["mDano"]
                        # Animais maiores têm mais vida mas dão mais XP (desafio vantajoso)
                        a["vida"]-=dano_infligido; j["atacando"]=18
                        spawn_parts(particulas,6,a["x"],a["y"],a["cor"],3)
                        if a["vida"]<=0:
                            a["vivo"]=False; kill_count+=1
                            comidas.append({"x":a["x"],"y":a["y"],"tipo":"carne","raio":10,
                                "fase":random.random()*math.pi*2,"xp":28})
                            spawn_parts(particulas,18,a["x"],a["y"],a["cor"],4)
                            if ganhar_xp(j,a["xpDrop"]):
                                evo=await tela_evolucao(surf,clock,ft,fn,fp)
                                aplicar_evo(j,evo)
                    # Animal também ataca o jogador (tamanho maior = mais dano)
                    if a["raio"]>j["raio"]*a["limiar_fuga"]:
                        hit_j(j,a["danoDrop"])
                        spawn_parts(particulas,5,j["x"],j["y"],(255,58,58),3)
                        if j.get("espinhos"): a["vida"]-=a["danoDrop"]*.25

                if j.get("auraFogo") and d2<j["raio"]+a["raio"]+30: a["vida"]-=0.75
                if j.get("auraVeneno") and d2<j["raio"]+a["raio"]+45: a["vida"]-=0.4
                if a["vida"]<=0: a["vivo"]=False

            animais=[a for a in animais if a["vivo"]]

            # combate boss
            if boss and boss["vivo"]:
                db=dist(j["x"],j["y"],boss["x"],boss["y"])
                if db<j["raio"]+boss["raio"]-5:
                    if j["atacando"]==0 and boss["invencivel"]==0:
                        boss["vida"]-=j["dano"]*j["mDano"]*1.2
                        boss["invencivel"]=8; j["atacando"]=15
                        spawn_parts(particulas,8,boss["x"],boss["y"],boss["cor"],3.5)
                    hit_j(j,boss["danoContato"]//20)
                    spawn_parts(particulas,2,j["x"],j["y"],(255,48,48),2)
                for p in boss["projeteis"]:
                    if dist(j["x"],j["y"],p["x"],p["y"])<j["raio"]+p["r"]:
                        hit_j(j,22); p["vivo"]=False
                        spawn_parts(particulas,6,j["x"],j["y"],(255,98,18),3)
                if boss["vida"]<=0:
                    boss["vivo"]=False; bosses_mortos+=1
                    spawn_parts(particulas,55,boss["x"],boss["y"],boss["cor"],5)
                    for _ in range(10):
                        comidas.append({"x":boss["x"]+rnd(-50,50),"y":boss["y"]+rnd(-50,50),
                            "tipo":"carne","raio":10,"fase":random.random()*math.pi*2,"xp":28})
                    evo=await tela_evolucao(surf,clock,ft,fn,fp,boss_evo=True)
                    aplicar_evo(j,evo); boss=None

            # ── Spawns ───────────────────────────────────────────
            t_comida+=1
            if t_comida>140 and len(comidas)<70:
                t_comida=0
                for bioma in BIOMAS_LAYOUT:
                    bx1,by1,bx2,by2=BIOMAS_LAYOUT[bioma]
                    tipo=choice(["fruta","fruta","cogumelo"])
                    comidas.append({"x":rnd(bx1+30,bx2-30),"y":rnd(by1+30,by2-30),
                        "tipo":tipo,"raio":10,"fase":random.random()*math.pi*2,
                        "xp":{"fruta":8,"cogumelo":16}[tipo]})

            t_animal+=1
            interv=max(85,240-j["nivel"]*11)
            if t_animal>interv and len(animais)<60:
                t_animal=0
                max_n=min(5,1+int(elapsed/20))
                bioma_rand=choice(list(BIOMAS_LAYOUT.keys()))
                animais.append(spawn_animal(bioma_rand,rndI(1,max_n)))

            # boss timer
            if not boss:
                boss_timer-=1
                boss_aviso=boss_timer<5*FPS
                if boss_timer<=0:
                    boss=spawn_boss_da_fila(boss_fila_idx,bioma_atual)
                    boss_fila_idx+=1; boss_timer=BOSS_CADA*FPS; boss_aviso=False

            # partículas
            for p in particulas:
                p["x"]+=p["vx"]; p["y"]+=p["vy"]; p["vy"]+=0.04; p["vida"]-=1
            particulas=[p for p in particulas if p["vida"]>0]

            if not j["vivo"]:
                await tela_fim(surf,clock,ft,fn,fp,False,nome_jogador,j["nivel"],elapsed,bosses_mortos,kill_count)
                rodando=False; reiniciar=True; continue
            if elapsed>=DURACAO:
                await tela_fim(surf,clock,ft,fn,fp,True,nome_jogador,j["nivel"],elapsed,bosses_mortos,kill_count)
                rodando=False; reiniciar=True; continue

            # ── Desenho ──────────────────────────────────────────
            surf.blit(fundo_surf,(-int(cam.x),-int(cam.y)))

            for c in comidas:
                if cam.vis(c["x"],c["y"]): draw_comida(surf,c,tick,cam)

            for a in animais: draw_animal(surf,a,tick,cam)

            for p in particulas:
                sx2,sy2=cam.t(p["x"],p["y"])
                if 0<sx2<SW and 0<sy2<SH:
                    alp=max(0,int(255*p["vida"]/p["vidaMax"]))
                    s2=pygame.Surface((p["r"]*2,p["r"]*2),pygame.SRCALPHA)
                    pygame.draw.circle(s2,(*p["cor"],alp),(p["r"],p["r"]),p["r"])
                    surf.blit(s2,(int(sx2)-p["r"],int(sy2)-p["r"]))

            draw_jogador(surf,j,cam,fp)
            if boss and boss["vivo"]: draw_boss(surf,boss,cam)

            draw_hud(surf,j,cam,tick,elapsed,boss,fn,fp,bioma_atual,boss_fila_idx)

            if boss_aviso and tick//20%2==0:
                nome_prox=POOL_BOSSES[boss_fila_idx%len(POOL_BOSSES)]["nome"]
                av=fn.render(f"!!! BOSS CHEGANDO: {nome_prox} !!!",True,C["aviso"])
                surf.blit(av,(SW//2-av.get_width()//2,62))

            pygame.display.flip(); clock.tick(FPS); tick+=1
            await asyncio.sleep(0)

        if not reiniciar: break

    pygame.quit(); sys.exit()

if __name__=="__main__":
    asyncio.run(main())