"""Le filet du chantier des déclencheurs : seize parties, seize empreintes.

Chaque refonte du moteur qui se dit « à comportement identique » doit laisser
ces seize empreintes intactes. C'est la seule façon de le prouver ; sans elles,
« identique » reste une intention.

L'empreinte porte sur l'**état** à chaque commande — position, jauges, stats
dérivées, sac, statuts, monstres, objets au sol, niveaux, XP versée — et jamais
sur les messages : reformuler une phrase du journal ne doit pas casser le
filet, changer un dégât doit le casser.

**Un filet se mesure avant de s'y fier.** La première version ne comptait que
huit vies de bot : porter `ESQUIVE_MAX` de 0,55 à 0,90 ne cassait *aucune*
empreinte, et l'inventaire des évènements a dit pourquoi — sur ces huit vies,
`pose` n'arrivait jamais et `jet` une seule fois. Le bot ne lance presque
jamais, ne pose rien et ne déséquipe pas. D'où les quatre **scènes
contrôlées** : ce que le bot ne fait pas, il faut le faire exprès.
`test_le_filet_couvre_tout_ce_que_le_moteur_sait_faire` garde cette propriété.

**Si une empreinte casse alors que le changement était voulu**, il faut
regénérer la table à la main et dire pourquoi dans le journal :

    python3 -m tests.test_empreintes

Regénérer sans expliquer, c'est retirer le filet.
"""

import unittest

from donjon import events, tree
from tests.helpers import (donner, place_monster, poser_au_sol, poser_piege,
                           sandbox, trace_de_partie, trace_de_partition)

TOUT = tuple(tree.ARBRE)


# --------------------------------------------------------------------------
# Les scènes contrôlées : ce que le bot ne fait pas de lui-même
# --------------------------------------------------------------------------
def _scene_nue(graine=1):
    """Une salle vide, un héros sans rien : on pose nous-mêmes ce qu'on teste."""
    jeu = sandbox(seed=graine)
    jeu.player.inventory.clear()
    jeu.player.weapon = jeu.player.shield = None
    return jeu


def scene_du_jet():
    jeu = _scene_nue()
    donner(jeu, "pierre", 6)
    place_monster(jeu, (11, 4), key="mamel", hp=12)
    return jeu


def scene_de_l_equipement():
    """Trois pièces au sol : de quoi ramasser, équiper, déséquiper et reposer.

    On se déplace entre deux poses : `cmd_drop` refuse une case déjà occupée,
    et sans ce détail la scène ne posait qu'un objet sur trois.
    """
    jeu = _scene_nue()
    for pos, cle in (((6, 4), "epee_fer"), ((7, 4), "bouclier_fer"),
                     ((8, 4), "epee_bois")):
        poser_au_sol(jeu, pos, cle)
    return jeu


def scene_des_objets():
    jeu = _scene_nue()
    for cle in ("onigiri", "herbe_soin", "parchemin_lumiere",
                "parchemin_panique"):
        donner(jeu, cle, 1)
    jeu.player.hp = 8
    jeu.player.fullness = 30
    return jeu


def scene_des_pieges():
    jeu = _scene_nue()
    for pos, cle in (((7, 4), "explosion"), ((8, 4), "sommeil"),
                     ((9, 4), "teleport")):
        poser_piege(jeu, pos, cle)
    return jeu


def scene_de_l_esquive():
    """Un héros très entraîné, sans bouclier, sous les coups de trois bêtes.

    Sa vingtaine de points d'esquive brute (0,90) dépasse le plafond du moteur
    (0,55) : c'est la seule façon d'exercer ce plafond, qu'aucune vie de bot
    n'approche. Il fait partie des trois bornes que l'étape 1 va convertir en
    interceptions — le corpus doit donc y mordre.
    """
    jeu = sandbox(seed=3, config=_reglage(start_hp=200))
    jeu.player.skills.levels["esquive"] = 10
    jeu.player.shield = None
    for pos in ((7, 4), (6, 5), (7, 5)):
        place_monster(jeu, pos, key="mamel", hp=200)
    return jeu


def scene_du_butin():
    """Huit bêtes d'un coup, et assez de chance pour buter sur son plafond."""
    from donjon.config import TOUT_DEBLOQUE

    jeu = sandbox(seed=4, config=_reglage(start_attack=99,
                                          unlocks=TOUT_DEBLOQUE))
    jeu.player.skills.levels["chance"] = 20
    for pos in ((7, 4), (7, 5), (6, 5), (5, 4), (5, 5), (5, 3), (6, 3), (7, 3)):
        place_monster(jeu, pos, key="mamel", hp=1)
    return jeu


def scene_de_la_faim():
    """Assez de marche pour que le plancher du creusement morde.

    `max(0.25, creuse − endurance)` : à trente niveaux de marche le bonus vaut
    0,90 et c'est le plancher qui décide, pas la soustraction.
    """
    jeu = sandbox(seed=5, config=_reglage(max_fullness=200))
    jeu.player.skills.levels["marche"] = 30
    return jeu


def scene_du_repos():
    """Un héros qui souffle, assez entraîné pour buter sur le plancher du repos.

    `max(1, rest_regen_interval − regeneration)` : à douze niveaux de
    récupération le bonus vaut 3, donc le plancher décide. C'est la quatrième
    borne du moteur — l'audit n'en avait compté que trois, et le corpus
    n'atteignait que sept niveaux de récupération sur les huit qu'il faut.
    """
    jeu = sandbox(seed=6, config=_reglage(start_hp=120))
    jeu.player.hp = 10
    jeu.player.skills.levels["recuperation"] = 12
    return jeu


def _reglage(**champs):
    """Une `RunConfig` de scène : un étage nu, et ce qu'on veut par-dessus."""
    from donjon.config import RunConfig

    return RunConfig(max_depth=5, monsters_per_floor=(0, 0),
                     items_per_floor=(0, 0), traps_per_floor=(0, 0), **champs)


#: Les huit partitions, en notation `script.py`.
#: Cinq d'entre elles ont été regénérées le jour du chantier 3 : l'épée de
#: départ est passée de 3 à 5 points d'attaque (la forme donne le chiffre, la
#: matière ne donne plus rien de brut), donc toute scène où le héros tient une
#: arme a changé d'état. Les trois autres — le jet, les objets, les pièges —
#: n'ont pas bougé d'un caractère : le héros n'y frappe personne.
PARTITIONS = (
    ("le jet", scene_du_jet, "TalTalTalTakTal,",
     "f07b58ae81159cfa8c0b5c0366885885",
     {"tours": 5, "pv": 20, "xp": 8.0, "pas": 7}),
    ("l'équipement", scene_de_l_equipement, ",Eal,Ebl,EaEbDalDalDa",
     "869623c9aad68b215fa482ebaa8a9f55",
     {"tours": 14, "pv": 20, "xp": 4.0, "pas": 15}),
    ("les objets", scene_des_objets, "UaUaUaUa",
     "c0fce7c892ea7643c2605111eb70cf90",
     {"tours": 4, "pv": 20, "xp": 4.0, "pas": 5}),
    ("les pièges", scene_des_pieges, "llll....llll",
     "f2ef0b750df617e1eb2b10b8489025b8",
     {"tours": 17, "pv": 18, "xp": 9.0, "pas": 13}),
    ("l'esquive", scene_de_l_esquive, "." * 150,
     "fce51b59c22bbcfe8fdd423882a1c435",
     {"tours": 84, "pv": 0, "xp": 124.0, "pas": 86}),
    ("le butin", scene_du_butin, "lnbhyk" * 12,
     "90cd05a70b45c6829993ce77ebedf04e",
     {"tours": 51, "pv": 22, "xp": 133.0, "pas": 73}),
    ("le repos", scene_du_repos, "." * 60,
     "4252b075da9dab04632e729862e5b608",
     {"tours": 60, "pv": 85, "xp": 61.0, "pas": 61}),
    ("la faim", scene_de_la_faim, "lh" * 50,
     "1ee5de18be56c3f914c998bd994757fb",
     {"tours": 100, "pv": 20, "xp": 100.0, "pas": 101}),
)

#: Huit vies de bot, choisies pour couvrir le contenu : le couloir vide des
#: premières vies, les vivres, l'équipement, les pièges, les parchemins (donc
#: l'identification), le tir, et deux fois l'arbre entier — dont une qui
#: descend au-delà du deuxième palier. La cinquième se termine par une
#: **victoire**, le seul chemin de fin que la mort ne couvre pas.
PARTIES = (
    ("couloir vide", 1, (),
     "86201ab829e4f4973823c510b7916c4f",
     {"etage": 3, "tours": 119, "pv": 0, "xp": 138.95, "pas": 122}),
    ("vivres", 2, ("nourriture",),
     "5993e657845c2021073ece2ecf39f5b8",
     {"etage": 5, "tours": 215, "pv": 0, "xp": 312.4, "pas": 148}),
    ("armes", 3, ("nourriture", "epee", "bouclier", "affutage"),
     "4b556060b919c4fd90af82dc6148c702",
     {"etage": 5, "tours": 203, "pv": 0, "xp": 276.45, "pas": 141}),
    ("pieges", 16, ("nourriture", "epee", "pieges"),
     "2637e0b840b24a076353a419286f85da",
     {"etage": 9, "tours": 548, "pv": 0, "xp": 861.3, "pas": 430}),
    ("herbes et parchemins", 13,
     ("nourriture", "herbes", "grimoires", "intuition"),
     "693d960b2f666af94e45834891f2d9a0",
     {"etage": 10, "tours": 445, "pv": 16, "xp": 754.8, "pas": 283}),
    ("projectiles", 6,
     ("nourriture", "projectiles", "rien_ne_se_perd", "butin"),
     "ef4b91bf9082e62043a71f35abf83c45",
     {"etage": 5, "tours": 150, "pv": 0, "xp": 217.75, "pas": 155}),
    # Ces deux-là achètent tout l'arbre : tout ce qui touche au contenu les
    # déplace. Elles ont bougé une première fois pour « Les bâtons », une
    # seconde pour les matières (chantier 3). Voir le journal des deux jours.
    ("arbre complet", 39, TOUT,
     "671d2640fc258c0365101119441b27f2",
     {"etage": 11, "tours": 589, "pv": 0, "xp": 1381.4, "pas": 461}),
    ("arbre complet, profond", 36, TOUT,
     "5f97c2f82ea28e39237f13fdd2dbdca5",
     {"etage": 17, "tours": 1046, "pv": 0, "xp": 2283.05, "pas": 736}),
)


class TestEmpreintes(unittest.TestCase):
    """Seize parties rejouées à l'identique, ou le moteur a changé."""

    def _comparer(self, nom, obtenue, obtenus, empreinte, reperes):
        # Les repères d'abord : ils nomment ce qui a bougé. Une empreinte
        # seule ne dit que « quelque chose ».
        ecarts = {cle: (reperes[cle], obtenus[cle])
                  for cle in reperes if reperes[cle] != obtenus[cle]}
        self.assertEqual(ecarts, {}, f"« {nom} » — attendu vs obtenu")
        self.assertEqual(
            obtenue, empreinte,
            f"« {nom} » : les repères sont les mêmes mais la trace diffère — "
            f"quelque chose a bougé en cours de route. Rejoue avec "
            f"`python3 -m tests.test_empreintes`.")

    def test_les_vies_de_bot_se_rejouent_a_l_identique(self):
        for nom, graine, talents, empreinte, reperes in PARTIES:
            with self.subTest(partie=nom):
                obtenue, obtenus, _ = trace_de_partie(graine, talents)
                self._comparer(f"{nom} (graine {graine})", obtenue, obtenus,
                               empreinte, reperes)

    def test_les_scenes_controlees_se_rejouent_a_l_identique(self):
        for nom, construire, partition, empreinte, reperes in PARTITIONS:
            with self.subTest(scene=nom):
                obtenue, obtenus, _ = trace_de_partition(construire, partition)
                self._comparer(nom, obtenue, obtenus, empreinte, reperes)

    def test_le_filet_couvre_tout_ce_que_le_moteur_sait_faire(self):
        """Chaque évènement du moteur doit arriver au moins une fois.

        C'est ce test qui a condamné la première version du filet : `pose`
        n'arrivait jamais et `jet` une seule fois sur huit vies. Un filet qui
        ne couvre pas une commande laisse passer toute régression sur elle,
        sans rien dire.
        """
        compte = self._compter_les_evenements()
        manquants = [nom for nom in events.NOMS if not compte.get(nom)]
        self.assertEqual(manquants, [], f"jamais émis par le corpus : {compte}")

    def test_les_commandes_rares_sont_couvertes_plusieurs_fois(self):
        """Une occurrence unique ne couvre qu'un chemin sur plusieurs.

        Lancer sur une cible, lancer dans le vide, équiper, déséquiper, poser :
        chacun a son propre code. Un seuil, sinon le corpus se dégrade sans
        bruit à mesure que le bot change.
        """
        compte = self._compter_les_evenements()
        # Ces planchers sont des garde-fous contre la **disparition** d'un
        # chemin, pas des objectifs. Le butin est passé de quinze à neuf quand
        # le bot a appris le bâton de flammes : il tue autrement, donc il tue
        # ailleurs. Le chemin reste exercé neuf fois — le plancher descend à
        # huit, et il redescendra encore le jour où ce sera justifié, jamais
        # en silence.
        for nom, minimum in ((events.JET, 8), (events.POSE, 3),
                             (events.EQUIPEMENT, 12), (events.BUTIN, 8),
                             (events.USAGE_OBJET, 40),
                             (events.MONSTRE_VAINCU, 50)):
            self.assertGreaterEqual(compte.get(nom, 0), minimum, nom)

    def _compter_les_evenements(self):
        from collections import Counter

        from donjon.script import autoplay, run_script
        from donjon.session import Session

        compte = Counter()
        for _nom, graine, talents, _e, _r in PARTIES:
            session = Session(sauvegarde=False, seed=graine)
            session.meta.xp = 10 ** 9
            restant = list(talents)
            while restant:
                for cle in list(restant):
                    if session.meta.acheter(cle):
                        restant.remove(cle)
            jeu = session.descendre()
            recorder = events.Recorder()
            jeu.listeners.append(recorder)
            autoplay(jeu, 4000)
            compte.update(recorder.noms())
        for _nom, construire, partition, _e, _r in PARTITIONS:
            jeu = construire()
            recorder = events.Recorder()
            jeu.listeners.append(recorder)
            run_script(jeu, partition)
            compte.update(recorder.noms())
        return compte

    def test_les_quatre_bornes_du_moteur_sont_reellement_atteintes(self):
        """Une borne que le corpus n'atteint jamais n'est pas protégée.

        Les quatre bornes du moteur — le plancher du creusement, le plafond
        d'esquive, le plafond de butin — sont exactement celles que l'étape 1
        va convertir en interceptions. Avant les scènes de l'esquive, du butin
        et de la faim, on pouvait porter `ESQUIVE_MAX` de 0,55 à 0,90 sans
        qu'une seule empreinte bouge.
        """
        from donjon.game import CHANCE_BUTIN, CHANCE_BUTIN_MAX, ESQUIVE_MAX
        from donjon.script import run_script

        jeu = scene_de_la_faim()
        avant = jeu.player.fullness
        run_script(jeu, "lh" * 50)
        creuse = (avant - jeu.player.fullness) / jeu.turn
        self.assertAlmostEqual(creuse, 0.25, delta=0.02,
                               msg="c'est le plancher qui doit décider, pas "
                                   "la soustraction")

        jeu = scene_de_l_esquive()
        self.assertGreater(jeu.player.bonus("esquive"), ESQUIVE_MAX)

        jeu = scene_du_butin()
        self.assertGreater(CHANCE_BUTIN + jeu.player.bonus("chance"),
                           CHANCE_BUTIN_MAX)

        jeu = scene_du_repos()
        self.assertLess(
            jeu.config.rest_regen_interval - jeu.player.bonus("regeneration"),
            1, "sans ça le plancher du repos ne décide de rien")

    def test_le_filet_attrape_bien_quelque_chose(self):
        """Un filet qu'on ne teste pas peut être inerte sans qu'on le sache.

        Deux vérifications : deux parties différentes ont des empreintes
        différentes, et un héros qui frappe plus fort en a une autre. Sans ça,
        une `instantane` cassée renverrait une constante et tous les tests
        ci-dessus passeraient pour toujours.
        """
        une, _, _ = trace_de_partie(1, ())
        autre, _, _ = trace_de_partie(2, ())
        self.assertNotEqual(une, autre)

        from donjon.config import RunConfig
        from donjon.script import autoplay
        from donjon.session import Session
        from tests.helpers import instantane

        def finale(attaque):
            session = Session(sauvegarde=False, seed=1,
                              config=RunConfig(start_attack=attaque))
            jeu = session.descendre()
            autoplay(jeu, 4000)
            return instantane(jeu)

        self.assertNotEqual(finale(6), finale(9))


def _regenerer():                                    # pragma: no cover
    """Réimprime les deux tables, à recopier après un changement voulu."""
    print("PARTIES = (")
    for nom, graine, talents, _e, _r in PARTIES:
        empreinte, reperes, _ = trace_de_partie(graine, talents)
        talents_txt = "TOUT" if talents == TOUT else repr(talents)
        print(f'    ("{nom}", {graine}, {talents_txt},')
        print(f'     "{empreinte}", {reperes}),')
    print(")\n\nPARTITIONS = (")
    for nom, construire, partition, _e, _r in PARTITIONS:
        empreinte, reperes, _ = trace_de_partition(construire, partition)
        print(f'    ("{nom}", {construire.__name__}, "{partition}",')
        print(f'     "{empreinte}", {reperes}),')
    print(")")


if __name__ == "__main__":                           # pragma: no cover
    _regenerer()
