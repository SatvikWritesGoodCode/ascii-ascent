from __future__ import annotations

from dataclasses import dataclass, field
from typing import (
    Iterator,
    Literal,
    Iterable,
    Any,
    TypeVar,
    ClassVar,
    Self
)
from abc import ABC, abstractmethod
from textwrap import wrap, shorten
from itertools import product
from copy import deepcopy
import base64
import pickle
from hashlib import sha256
from difflib import get_close_matches
from zlib import compress, decompress
from datetime import datetime
from string import ascii_lowercase

"""<maps.py> A module that contains data for all levels in the game,
both built in and public. It also implements the most important classes
used in the game, such as the C coordinate system and the GameMap.
Finally, it implements the LevelData class, which defines what a
'level' is."""

type Result = TypeVar("Result")

class SerializationError(Exception):

    ...

class Constants:

    """A class that defines constants used basically everywhere
    in the code. For example, X_LEN and Y_LEN are constants
    used as the working screen dimensions, as they are also
    the dimensions of the level maps. TOWER = 20 signals
    that the Tower is the 20th level."""

    X_LEN = 63
    Y_LEN = 12

    TOWER = 20

    NaC = "%"

    """NaC stands for 'not a character'. It is used in GameMap objects
    to represent something that is invisible or should be replaced.
    It should never be used for anything other than this, as that diminishes
    the meaning of the character. Here are some of the uses:
    - Map.__getitem__ (index out of bounds)
    - Patch Templates
    - Icon Substitutions in Intro and Ending Scenes
    etc."""

class Charset(ABC):

    """An abstract base class (ABC) for an immutable set of characters. These
    characters must come from a universal set UNIVERSE, defined as a class
    variable in subclasses."""

    __slots__ = ("chars",)

    @property
    @abstractmethod
    def UNIVERSE(self) -> frozenset[str]:
        """Define in subclasses."""

    def __init__(self, chars: Iterable[str]) -> None:

        """The argument 'chars' must be iterable of characters, where all
        characters belong to UNIVERSE."""

        for i in chars:
            if len(i) != 1:
                raise ValueError(
                    f"expected iterable of characters, found {i!r} (length {len(i)})"
                )

        self.chars = frozenset(chars)

        if not (self.chars <= self.UNIVERSE):
            raise ValueError(
                "invalid characters found: {}".format(
                    ', '.join(map(repr, self.chars - self.UNIVERSE))
                )
            )

    def __repr__(self) -> str:
        return f"{type(self).__name__}({''.join(sorted(self.chars))})"

    def __len__(self) -> int:
        return len(self.chars)

    def __iter__(self) -> Iterator[str]:
        return iter(self.chars)

    def __eq__(self, other: Self) -> bool:
        return type(self) == type(other) and self.chars == other.chars

    def __hash__(self) -> int:
        return hash((type(self), self.chars))

    def __or__(self, other: Self) -> Self:

        """Defines the union of two Charsets."""

        return type(self)(self.chars | other.chars)

    def __sub__(self, other: Self) -> Self:

        """Defines the set difference of two Charsets."""

        return type(self)(self.chars - other.chars)

    def __invert__(self) -> Self:

        """Defines the complement of a Charset."""

        return type(self)(self.UNIVERSE - self.chars)

    def isdisjoint(self, other: Self) -> Self:

        return self.chars.isdisjoint(other.chars)

class Charseq(ABC):

    """An abstract base class (ABC) for an immutable sequence of characters.
    These characters must come from a universal set UNIVERSE, defined as a
    class variable in subclasses."""

    __slots__ = ("chars",)

    @property
    @abstractmethod
    def UNIVERSE(self) -> frozenset[str]:
        """Define in subclasses."""

    def __init__(self, chars: Iterable[str]) -> None:

        """The argument 'chars' must be iterable of characters, where all
        characters belong to UNIVERSE. Additionally, no characters can be
        repeated."""

        for i in chars:
            if len(i) != 1:
                raise ValueError(
                    f"expected iterable of characters, found {i!r} (length {len(i)})"
                )

        if len(set(chars)) != len(chars):
            raise ValueError("duplicate elements found")

        if not (frozenset(chars) <= self.UNIVERSE):
            raise ValueError(
                "invalid characters found: {}".format(
                    ', '.join(map(repr, sorted(frozenset(chars) - self.UNIVERSE))
                              )
                )
            )

        self.chars = tuple(chars)

    def __repr__(self) -> str:

        return f"{type(self).__name__}({''.join(sorted(self.chars))})"

    def __len__(self) -> int:

        return len(self.chars)

    def __iter__(self) -> Iterator[str]:
        return iter(self.chars)

    def __eq__(self, other: Self) -> bool:
        return type(self) == type(other) and self.chars == other.chars

    def __getitem__(self, ind: int) -> str:
        return self.chars[ind]

    def __hash__(self) -> int:
        return hash((type(self), self.chars))

# The set MAP_UNIVERSE contains all characters used in GameMap objects.
# This additionally contains any characters used in their creation and
# interaction, namely ! and NaC.

MAP_UNIVERSE = frozenset(
    " #*LlAnNX<>V^_KkHhx@SF:-|'\"?/\\`()[]{}+=$;.,123456789!" + Constants.NaC
)

class MapCharset(Charset):
    UNIVERSE = MAP_UNIVERSE
class MapCharseq(Charseq):
    UNIVERSE = MAP_UNIVERSE
class Lowercase(Charset):
    UNIVERSE = frozenset(ascii_lowercase)

# --- Save strings for the 50 main levels ---

GLOBAL_STRS = {1: 'Gb"/$9lJKG&1&MK*."Qnj>r*L\'<+U:G-\n'
                  'I0:)Q@Hr4sEu.:/MMeh/R;9]p@8aPlhZ4mu?FindF)E+:+(_U_\n'
                  ":$>4P$Ytqr[:83V\\#Ko]9lS_<U9`en_q6%#@r2D\\Ie6=tV%';6\n"
                  'AQTh^<m1F1pK3gu-QR%_Vn59so<H:*RpG]KbFtW!28A!eFB];=\n'
                  'GW#YdV*qd2ZUmRBm5D/Rm,VWgV=6C=Sd"*2g0nT69m#J(3bWam\n'
                  '6M*Qrc/:l"\'8N!f_rH]`5\\o:^tdnr]4$=NOJ/8c.n?.niU&rSc\n'
                  "7Q\\*kt%FB!K*>CocOWWp^sh2r4Ki%@\\76*a:/iQ#Tn'2&/2&\\B\n"
                  "VBu_#FQA42uaRpHeo'kge^hWS19-f!7Dpj-\n"
                  '6BBe1Zd"9]`h?QqB0D?hRRP4r.:Ubh/*K2^ZrS3mQCB51Re?X&\n'
                  ')E-\n'
                  "/fgSg#D\\ds%?nf+TMFkui;FiQXdNJCMOUVb,&GiIij;6f!\\?'d\n"
                  'a_Imco;U3HVbH/_L,H,ARC-\n'
                  '.$q9h#eP^S(9fp>OhqpXR&VZcjoKH=g]F[M..i)3#^$)35s:-\n'
                  '?iCH4fZRom&r\\6V]r`1<pa-+J<7u,;rpT%-\n'
                  ')#S,`!\\p[I/GF1EI5_',
               2: 'Gb!#Y9hWAh&2dRhLE:d-`PWHE<Q$5R2G&8#+tB;f_-VJUUpDD8\n'
                  "1ne'+*X'1Fc11h&<YUdI84D9]b;-[?juqQBk%X/S\\@=7r2-\n"
                  "%<+#E0KI<U'e0:*:R&0Eb8gh5hQ-Sa5&l@(OlHH(-\n"
                  'bF[7b8T]oQ]k7`\\Jh6,mHP,hsONE/7LlKc&6s<:Lr;F<RIsg3]\n'
                  '\\e;OdJDor+0pV<q/W=rf<kYY+k:EM,-\n'
                  'X62;Nn]D8Clmol:mV4H!bDN_pHmL-\n'
                  "b0bZ.o`0'?W6`XbuB!sd<GREeJUV0.7e&'O/-\n"
                  '+">EXZW[TZr^Sd9s"=n@Ym([lo.IM)JuZ<t-\n'
                  "c=?2&>:3*5[Fjeib#[Qk>3VGj'.SoIWmo+J40_m9*>n>b(.=$c\n"
                  "ho&Gd$IGgj3:B:6'WS]Y,RHL1^qFQD4t0W$Z--QfsDd;cHgsW(\n"
                  "V8WE/R+T;dl0u?d,_t_DK4Xg]S1$=P'$I'$D#cL",
               3: "Gb!$DheU_,&B>6Oge3_rH5(aqiko(ggGGD\\]Y(To.RajTqC6'?\n"
                  '9X;J[HfTt&4V[O:hd$0^s&,&,=71iMUR]h-\n'
                  "&iR?Xht\\r7RElDXIIH%)^':n?(-\n"
                  "c4/<([$O7sMis1QUWkaaJd_T?q)s0V,+L3%d'odt3L_P)mqq1)\n"
                  'E7<a&rNO$NePg98*>M3)HoEZ:Ua#pGGT`bU2VU3rG_TPe:AlWt\n'
                  "/rAhbnfq\\:/XV28`_^s'H&-\n"
                  '#)`/(Rag1GX\\Wld[;Au[j)\\ENH>Q>jQg7p5hfmTh`G4H\\D.A".\n'
                  "pD4P?;H.R'm5BR`>.Z#(<'Pa0Qsc&S^Tua(e(l([W7@LQ[-\n"
                  ">S1!rWq'2ftnilFMmW1:0'jQYOt+38^O#gJ/'`<(Uh;l?@P9Y!\n"
                  'SW1FTO,,2\\11(mZ0(;q<VZ0`dWkLH(K_!>XZQU@-\n'
                  "OK3=7\\L8C'GMp#u!cW9&N]U_G!pHo)bOq&.'b1/uj^p>h67Hfg\n"
                  'Uoi!JD$r3KSbV3K8H?;F&#)%LIl$F-\n'
                  "=QUDu@`4InCUq5D`;LW_'=LM_R16QfRX$2=R%s1X4m?ff#T8$V\n"
                  'ffp&KnBQB45INO3unlD/)p?=^Y\\US=$(%0c\\_-\n'
                  "[`'5D[\\6<9oE2:gpiZ",
               4: 'Gaua<cVMD3\'ZXLtE*4<G"5L!JJr,%qN3R@7A(2>A0u5@ph.RgK\n'
                  '_hFe=K8JH3oD/DI7Y!3p<*[;sI\\^9,pO2a0f=pX"mU`lEUWg$q\n'
                  'jI%tu"X`*["J\'"?CuQTB<g7?!\\Q2]U76<i!euU;p77B.P@(?q-\n'
                  'm/%<\'A3#(iX8pGRf^jZ*0<e+\'fRj\\oI"td2gHe&GTcBRr2um1<\n'
                  '>`b&@"&(trFUWFW#Vj!<@_%bb]h=Jt8Th?BJ+J1dQ8k<>G@25=\n'
                  'R.iApI-Q)CU_#Q?@[L.d:gJ^*VtGZQnZ8[Ekn?I-\n'
                  'B2tg3Z+<VB66]DJ/r6b[05K)h8K,SFT#H(^XrQ!l&&I]Yr_LPU\n'
                  '3S`M^0<LmNc-\n'
                  "'H/U3S%[G%i]^>*+iN^'fj&bBc:*FB0aJRo_U3_hr<j4q>VGPk\n"
                  'M4C)2p0QoWdf@qt#dnj%`c`@(REe3s7]lBG>8h0A(:<!=((UCX\n'
                  "k*r85E/AXe?RpXfa(,NiB1^7&%A$>utSeaeka\\'!3+a@8J06RV\n"
                  '=VfeW_#aKjb+L03:fh?i',
               5: 'Gau1,95E9I&:c:rilh$lkE,"_5b15U\'Kn"hQNg%p6>Hk64bg8.\n'
                  "<frTe1>6l/%u'.0[nQd>eo$XSZ7X7NC;dhU1]-\n"
                  "R@G3@2P]C3u\\ZY'f<?c5`[%5&h$Q3d9(8!?-\n"
                  '_3T7D\\miU3ZQ>(KuKA#MC<nDBMX@N\'Z//M2N4)]bo5dqKS\'b"Q\n'
                  '=A7N+\\$D\\Sq=$)(pP`I(uo7X$9a%(5Emr%>JiCc=/kHq-\n'
                  'o1j1<VeUe!%o"$)_@:W]b.eNrWRc:T3``FYb?us"moDAiJ8q1Z\n'
                  ".X1lQQ29a'U'!.*Z3EgL9f3R1F_Y7aATO^\\g*K$/KH;S5m=`)\\\n"
                  '7W/>.$_0V$a$.euiQ0b)<n=Z8/B/--\n'
                  ']I(,^>bGD093t$BN6&>`(_t$rB"ktp7`/LB`>@cCMN0bAsm,,Q\n'
                  '+TQ.X2$pCc%RUMJic5fgO?<H4iNK7*3`Hk*LKTQ/YDit<BpI(J\n'
                  '3PG:)YKEEr.Vo(L[aU@p/=;pG2G>;g8UaY((5)c-\n'
                  'dFfdpn"=J=E!]?>\\)-\n'
                  'i3N&Ob<Ui=9ijLOk5Hmfsjl11T&Jgb9!S1\\**O&g@eq!YJRI*.\n'
                  '*^t$,Y&5!lsR"IG8gJ?%fpN9pMO<_`c?Ff_b',
               6: 'Gaua<9lJKG&;DnBjV%5#V&ZDmi&%GPH_!-\n'
                  "4/efHoW'mXbXrQ$d\\i0)F]Im%k89!H*_]Rg'@MeSYa,Y3H_II;\n"
                  'fj4Ti5B30Ps4oP2WrTN5)bOu2?Ka2"[m!SFb]Oo:6@OXZiWYn1\n'
                  '[(_Vgq(SI0pK1sAmDIt:%[i%sS5IuJ,![][oqI2\'"A9/6Ka$Xf\n'
                  'n_30JXoFb^cA;NS)I`Fc=@gW.MoC)GhjceJ\\T<Os&;L+:/kPlF\n'
                  "G)%M^n$D;T@@>CqeNN?QeWcPJdhisgki,>,bDR$HI'16&9B87V\n"
                  '5pD3f([OK?:UbZ%LFW2a?Wte]<c;It!Q0Bcq\\(O+`LK%S\\T6qm\n'
                  '(QM#"T\'mHIZ(Pc1<4mnnan%j1fit.IL]\\A\'Vc$8RrPj<0A2\\W9\n'
                  '>EYO+b4fbQpa,\\l+HI!XqImd-4Z5lgA4)n\\7\\%S(iSaeC/QZ$-\n'
                  '\\[s]</misc_M*%sXQ<%,3$<\\8%Ug+1%R6":f\'j)%1P-\n'
                  'sd8%of5h(;o>40EEP-\n'
                  '6t[pO?`f$`Y7B\'\'?n$lHcQt0#duX`@"gL3,(LZ\'3Kutu+.L-\n'
                  '?B7j&.9jA)k7B3;r5Q<2(.-\n'
                  'Y(H$Y"on2FDP^9[&>mN34`u>VWD\\NTqa>b$)&T]VUU&\\7]\'bM/\n'
                  'hpXe@>:,`!<c0l>l',
               7: 'Gaua<9hWAh&;H0F$<#SE%m>/oGc;lFT:<3cJuFJ0"MGT(Zl;q#\n'
                  'D+TW3K:qtL3W<Bpd8o"Lp/&s9G\'@ORH1p&;H/&;Q.rL&B",]&(\n'
                  'Kft=u6L!?<iY`b4D<b&Q\\th5q[Ac\\(3>!Rc<gC+fM746e`>\\PG\n'
                  'Uqq`[KA\\1<5U^l!*$>qKWQ-PN`Xb1Xa&dp7m`-\n'
                  'q<p^P(`\\u#E_`Ymo[&4CW`gj\\;F<8.DjU@RmM@j&-\n'
                  "uD2)<^+TnotLJ'YN@s(Od*2U_S.Oe9oS+TL<>+q8Or43$=8;4\\\n"
                  'Z8cEPFj*+=[4,Hq=U)!64OPUB(%"sQ.ACjXdPpP`9Wqdj\\"<_e\n'
                  "e].`1b+?\\`Rf:3P;rFbB!^Z(;!8GY6?'BE+9if>ICpbkC!Y!J;\n"
                  '&"nm)X/O8-\n'
                  "$hT2=\\43jKX@)L+:cl$!&A$Ga5'YN,!M`cJ.3[Sj&,cNAtf9_o\n"
                  "I*%JE'-\n"
                  '+[Qd\\tS>oLht3\\;0p_GSNbU#ZmFDDP]a^I2+bgpSpg^6!Pnd',
               8: 'GatU192!/f&2m_V,qY@=]gfZa+uYK?8UDpX/YW83Y=1@kXsr(.\n'
                  "RSr?8d/2Z>s0&\\mdd/3<QjHHLfpVZuS&t*qiR`'hDfsTEnJ3eI\n"
                  'Mrk(@+!RdlU?U)r1Bb(^>><"MR_!4*CV&?0bc]XImQ@.4r<8d+\n'
                  'j4>1":cue);>_E+!%j/W1^7,\'TJ?/e\'L(LB"5\\PL,i<#9p#N!m\n'
                  ".7EGRTo'%O.4S2k]@)P#)-\n"
                  'tr:74("1O_^dQo/6[LM&5$W7Nc\'917H<YPm1cDr?&q#odkhig4\n'
                  'Ll9OMW.&:suNV"u[^laYKKSC.@Tb3!\'koEY#.7W[+I?q^dKEYD\n'
                  'DMigBglA-\n'
                  "/ASC6(4cFasLalN'PZ,O&Etr4p22h=!5;o:SGiVRu4iq2YLB,C\n"
                  'fakRCu!pajf>7jTYeXh66OFomh?(l4lAH!]LRQZ/X(mi]e=HDr\n'
                  'ZW3"rh.kFT2/=8ei]HB29S0,UL8a&oBQ^.p#;loF1r@.5AroFr\n'
                  'L85h6eJgU],_`^N=[g`gM\\7e-\n'
                  '%SFB:<122h%$Q1i+&g!KcparX5ai1%9u6lcnS`_bi.P#&lc`c',
               9: 'Gau1,c\\p7;\'ZZ26$F2[V("VE$#cgKT^W<cFX:(aH>$+Vj[)aM<\n'
                  'ZRM9=,dU)R$[R:]TDu*7`KFhF2H;Re&E`r6kC#-\n'
                  'R^>/^:4M5ZV*THPtI"IDq9"=UJ#PLimeqp=.iIMddq;G3/"n<8\n'
                  'g`Nq7c"VEhe\'Ae\'h<1:/a68;VD/-D"h=D%5S_Ef>G2<"&$-\n'
                  't"Z.oSjo?V+\\[0NM"M[Ydr.iPjeR]U%=p]k?>4ZOiF&fp_s9%h\n'
                  'g\\;W?<KKY47E2bco8<)*crIP-IucLD*Kl^IAYE\\N\\gXg]1pd4e\n'
                  '7sBpHtZNTF40;aeO!>V^F.>Is-7ZW5eB`u@(-c-\n'
                  '=ug3LD5&T`FPc:q;eOOj\\AjenbX/SPI^#kg-YRePGtP^4@*i,M\n'
                  "oQmN$Q2:3kFo(i$7NK73FlPjP7Giscf'cffrNp/O3X/D.YOCNS\n"
                  "4IAK5<pSpH0%'nSeZ5MtkOj,6q6^WgT;scbLSn.oe7(:FlgfWB\n"
                  'Mt:2YcXNl@.Tlq_&sXAra!@+n2t8.b\'9OWX,kD+&j9">&a.Y/M\n'
                  ".A'!@r0U88)8S.mSGOGh31WO,j:fgKOI>8XUhKZ.8h\\R.",
               10: "Gau`Qc]=8T'GdfR%g3N.c,SK`*kE7W)/*aK`?tT:(i?R8?9B&\\\n"
                   'd$^`8"TkHr#F"gE2oksMTqsHM:l-\n'
                   '7[lNH@`R5a%#hAb>=rEm$HGIG7Zp>@P%MH9d]S>ksE%%a5)j.d\n'
                   '<.G%!B5kR;:NG+SiZSN?Jo*eN]<B?#ihl;MYS.A/+^\'"fnYl`F\n'
                   '$IEHZMZep*2frf]SG_7t&7:[%UEIOY7iH,N)Crs9GX6BruqGc6\n'
                   'lOk(&55#>mSJ:?hF7MV[MjRINFt:GOk4M\\q/maS,rpMY7"&@a@\n'
                   'I,>s!V4NhGd8.[%P8OK[%M&QCqDS47d%@;!aTcWRA(<4_[1m,Q\n'
                   "G2A#Q/?Y8EZ0mGKGDU_LqU1tuPYRdAkq5S&hUJM'I0P\\7YaWu_\n"
                   '"toA6)\']!f:=e.P,)gD\'fb](Qg0D-aNT+O;PRRf2GmI_t-\n'
                   'f:g4OQ)*=o"M2b[bBMu6;)6VkPh>Fo"FZ\\(Tht#S_,m=@I]\\@#\n'
                   's@>?ut]JASKe(s?dQ,]5A27%K9.dXEu3F9bjjs;1o@#6-\n'
                   ')3[4)V]?/2*dp)"A*4md`=Gd.%#9`d\\==aajRYZOud4bZlp^7@\n'
                   '("=X,*6,$AVY/(@:,^?]ubD=/gMC+^72:FCuFc*L6o[>u8#4YG\n'
                   'c8kgr-]t)<uNe^G]4W%9g6K#d,,_-\n'
                   'PXA31V<+XCP>/`:m5g;/Rf0,V55`t-\n'
                   '/miaC^J[c\\8u\\bR1SIHtq',
               11: 'Gb!$D9l&K;(k?Cjd111&`mD#T64_2HZMHqnh-\n'
                   '="5Z;J1u+hO$abOQY4NtApu3>Aq!HeZ144$-\n'
                   'T.,um85L!G`FZ9BAFP-\n'
                   '#fZIes@sPH,"F?c7.#&]6l4ILQJV^kQ?[N>TNpDOhZrRAl\\L.F\n'
                   'IOkA[Y<*Y.FsXbD)#R#4\\FP%l2!kJn2du5SVni-\n'
                   '_)Jnd#TA+:@IHRQ\'`":KS.T%(0ri:?hjIF4s92.j`lF&iWeKI_\n'
                   "s6h:$A[f7s*la'Kj\\#P!_TZ?(H%l@A#L0mk,8rnCXV%#7A@4Y=\n"
                   "^I:i?'B.m>s$3dpMT#$#>j:;L,!mBDQtmX`Bfd]g'B*F<im1#S\n"
                   'iWt@K<dn7[GGpUA?3:qgFY%s@Fe4YSjhW]6aim7[lRi@IML"+6\n'
                   '7j/m]sTF$G"(6@5dhK#dU3tFD8O\'Pg]3R7P&K=d*L>)bZX-\n'
                   '?*5k>m;1@OL>=Fm6MLssb]\'*Na?(J0(D"DKglQH]r,8mFR9+LE\n'
                   'D,<U]eTWme#4O(m%`8Y4f/OQ<*k:J!Sk;4<>&Z=9PV\\8\\Dn9[R\n'
                   'khds(K#@+8]L:;AD13-\n'
                   '?8!EBW&a\\ka?iUBWmEY3oF^i,`ctSE_[FF+!]e_+iuO',
               12: "Gb!$DcYq8d'ZZ&21_,W`V2%Z68=juBB^-4c-\n"
                   '>P8.65r6&#mma?fo8@VQ6/^#,DSkFh)?DT02B+na%8c5LXF`7a\n'
                   '^;e.TD*J,?U+JaAbX%3F3#H:A`),DZ8$=s6c@>EP#[b-\n'
                   '"Sg&YNc!qr>M))*Q900W$pR8NI,K@#RPPX3&g3JC`BNcW9X4`p\n'
                   "mOJo+T4IEnT&.6tn/\\4?7lV2iXrTd'hd8(RE1bJV?O4/r+>P-\n"
                   'nC[[Tmkf.@"KDPKdU7hiu*49[eAsZ\\rs*Li[0Vm\'\\/1\\<-\n'
                   ')Qf%rYAG-FXQ^:pceY[kCHl?@jjL8tV]a6O8sS(/I=aO/oH"WJ\n'
                   '21&poq(V/[em(Al8?a@e!OmLUApN1\\;)e>t<i`]==?G:2A,(i7\n'
                   'k<aB0f0igUoXN/RB?aUE;0%/nmipS1$O6:+:fgT@.^/a[[redD\n'
                   '2]_f:6[Lu*@o.Z1>o-\n'
                   "U/h\\aakO*h_@H$'mWMtqrNjm+0crShn'hHU8)4f\\P1p3fh9L<@\n"
                   '.qV:`[`EQZZTW=[2#Y=UDhO+H?_4H5Jj?q5@%fYE;&b0(J&M_G\n'
                   'k*UdS?h\'FT6\':e&Sult\\K$%R7qN[5".S*hsB(Vc,[IGd\\Q9/nK\n'
                   '2k_C6_JRX--"n759i.)FQ-:L)4e]mr.p9qd710;e%"$i',
               13: 'GauHI9i&Vk&@E+FLMeqA#hKtJBT,8N>MqnYe/0JddAo!+]!Xs%\n'
                   "#ULr*'><kZnc-\n"
                   '0%/aRWgHBC_/ST\\W=c.eZYIH,*UF)CIuZ)oPQ9V79$"\\cZ?WGt\n'
                   '6/@uh$)Y[Z9HY#r_VflR^`ZI?&%L06C:>JTaQT^t]!K1?El0-\n'
                   'M@a?!t2q)+;7ucUjJ3a8eD4rr_,.Xn1^p#:9@^g+.h;e+WQ:!0\n'
                   "V.5cl`4OTUZ1Hk$XVYiV!>7@&\\^?'hS.X:KGE_M%Vb?baXJug-\n"
                   "P(^'jeK8gOP5V=KiDZ/$$QcSlA-\n"
                   'P]*FHeWZ!l&?G^+gYdC.#)[\\A*HLb[Zk*L-b(a-\n'
                   "dHW`78Aj+fo/ET^=13$o'P5#!hp2,Im_FQ2TB/BerA.[9!cmhg\n"
                   ",_'9*diPA/9eJ)crOfom%i:ojUX`(I)-\n"
                   "ABJh.l\\^,;F=tl^Po7mtbgo6ISUC!?;'g3SF@D2B-QtrkF-\n"
                   "1*'V9o5uOLoT%SXp?[C#iP8_Ak)7BX^2GT*@TZh4_O075*l6U5\n"
                   '(/m[,ee_efA`0Fk3X=K[a;^p.1\\J^2M_Ccur)=W&h@g29UPTWt\n'
                   'EtSCC^B;\\^[ee4q0V@.rF%@qfSeH,<5N(;$+g#',
               14: "Gb!#YcYq8d(aW?o46/)t9KhIrM*kK4>CNqndgJMK`me$UJh'0*\n"
                   'i[e*YUhVYe&!Pr>)^#!k3,Y278\\5^W(jT!FfO(8ChrjY/rqP+6\n'
                   'rC?d#d";Ap8pmGBJBFKHK&5G=@YEn]BMCA01uh82Fn6nWc(:X\'\n'
                   'oG79W"KG]2nN:orm;[*!-\n'
                   '=d]3*&u"Mm7DC$ZnfV,#jD6kSrt7g_,"bDJ6S[nC`GW+KABLQ#\n'
                   "+ka3+AB[?Y5c6bTFq;UI0B##60?K.A1HDcGJkWqkP\\f'k^cgsO\n"
                   "OJBN*qpj_2oVJ`8^s&W9$a1bp+Q5DEE&:[YFq[X<0sSO'NLq;4\n"
                   'tN6e:YO;E5/6II4VmW8j!a[GmV\\#6mJXQ!rim"^H]#VFg!)WOF\n'
                   'JH(l6.qN_OeNX<%Fm&8BbZih62HRWege,9/c3lSQV]U$^3#BVV\n'
                   '-JSWPChUq34aa9R#1`Gk,RlJE$)M==QMjumBsBO)QD4>Ir0\\56\n'
                   '$-\n'
                   'G\'.H_kD,pXE%T6_5U)j4np?bCO;YrsF"Hl9HQ0Y3.I,#amVDol\n'
                   'A@PP<#i_c*3]?7.T;@K.9YPq&;dJCQ/VX\\e5U.?86uWFIiH#`J\n'
                   "+UK]ma%$^r+45-\\T3Za,rP2!Y$c'?)-Xi1lg<;'4;W-\n"
                   ']gmSUZ]Q8\\S`@q/\\Tn=?.7?.k)d#cFtCPY9j:Q.?-?rC$s-\n'
                   '@h%V_?2X(f)o<nV"b[4E>-3;iqu[.`k',
               15: 'Gaua<bA5it&;MdqOre.UBSDIPdu4)gdDM+^?Q(>0#`58%p/m1n\n'
                   '.ndgHN22-\n'
                   "l:e:#$lh(5E8m$8LhR.'k<'PqX27k[%bXgU&a1mMl8*r/Z:Tj1\n"
                   "=Sg2\\b,(E?AHKQsI^b:'XRUMhUp5*?_mMf]H'AJsX,P5s_7/9_\n"
                   'i<9H1D$49#BF<J8N^FXpUTDK!Yop>.]?J`R1+@l&aI"``WM=^i\n'
                   "^H(Tob*KiV:hGo%Y9IUIR+VKApU&'fYD>\\lVTQDC+-\n"
                   "YR#_>:BWq%n:tujNcdif_%M*$$;q\\X3ig3'5,#I'dO\\4O+b8LA\n"
                   'h;\\>4^7lb6ADDT.]eHg]D8]_l8fF$I[FQMDl4e[kGlnWq3E+G7\n'
                   'IZ<X-\n'
                   '4o:C+m=6I1$^m4b%/atC.#c]\'N[_.".!*GR^$daZ6:@=#AEMl[\n'
                   'm6aiY1&iT5EA-\n'
                   '+fP#X>0)JBkSo\\ogF[Ao/2AVG#3+(kk0Mi;3X9\\UJGmQ;O?X/W\n'
                   'i_RL",#>\'ti;nU20qL\'?]@>_DV,)c&,3@i^:9Q/>&ReFEYc]Oh\n'
                   "gBSJ$:dDP;hfB?h'nuSC931Zu#%)lpX<WaJ^$WLT:l[!W<+htg\n"
                   "k.dCV3Q*3?(H(#285rg-%:)$+KoE'5IGc!X$#@h;V3-\n"
                   '6]i*/92b(h4r!7ZLt>?5.Xhl\\qQO2"j`*fKI3.NM-FP2rU1hV>',
               16: 'Gatn$hf"]T\'ZVNNb_J\'Q:$/mn],9Qbb4r6-\n'
                   "[P'9'<u0E+6skqa^gWRGE#ZUC4rEtk^3TX+Kpi(>([)M/D/O^b\n"
                   'iL<WX#<4s:rV<^>BDFS(pFkG/Y),>1Z29@YGsu?RRmn+2^1Nu#\n'
                   "k)#cL_rjE,:/#/,S<=C]'TZVmn4>r!+X(h<dEi&`n;np[kr`5q\n"
                   "')O;[-\n"
                   'oqC"`@,odd/^%cL;39C0DpjiDL*9ej)Oo2as1H/<=.b+Z>PRYc\n'
                   'DmhBWoO41Krd`l"PJDC[4sL<Q!ESlSg!F-\n'
                   'W.dMcf?!ffjM1G1rM.H5K^o_]ouhB(fq(X+<V"+AG4]4rqeFAO\n'
                   '.$MgQ%+f3Zg:IMUTmkjP[`X6q]qd0*CL(eg-CRKj<U#Mh".;Z!\n'
                   '2;^Tg*iimW^,rn=!]bH^PL[.6Zs&bm:*>e1=E^[U41;#drn""]\n'
                   'WpU*P6+d.D=^=NUHWABmAC+)U]iLA\'8Z/@[MZ6FJA?hs95]"2"\n'
                   "A0%p>Kn)[O2kK1o5(q%'kj`A7)<V+!'4e^k]Y(`SH38h`),1t<\n"
                   'GXU[&6F,NVM8KE<2Kc1N_<&^J:)?DKNm>b:VZSLpN6di%fp#,H\n'
                   ':"">P<)jYhMN0[&"s*q@f1g*9d[a=S!6_ahp;jIhl=6i0[LTaC\n'
                   'gTI4Z*>n+2@p;2-GH=Y_0H+)]T_]J0-LPs',
               17: "Gau1,gPaNG'Sd,ueq\\'-&@WC-\n"
                   '=a\\m;h+acW[1Bhk.Z4K6`A`oN1>N8KacoA#XXNE1]QsF)S[<S-\n'
                   'k2Jk2q\'DQTrL7k_3FAq;caU&.SiqAt"eF$sA@`oVf8QHEA24[O\n'
                   '+<Yle_4`kK`!1DQ,JtB.n-\n'
                   'E7^V%<.jELI7V9uAqR5ma.uL\'YWQB=f9J$(5<H\\"8_8qIBZb@/\n'
                   "ha)#'j5!_ctblYLMtAe!H6O#@Q<d<-\n"
                   'iu+e.AkP;GqiK<0=71Pe*2QC7jGT?>F:1B,uWS*eMl_!4uC]En\n'
                   "$).-u)4).+Ghh@(H9;2Z'SD7r%dKobLI*n&huD-\n"
                   'M[a$q4`[iQh=Pqr/-$]5YsU>c#]tICJ1n?;G/*2$.a<,-\n'
                   '!8^_(Tl3D<27,U6WsANDcZS_J+,enGQ"?rC-\n'
                   '%XIcbeRc@2539(WllMGi;DsV0BcLJ#^/%1OhIf]gh0+5H;ImRV\n'
                   'p/,#+>_A[ol5hpb^r=ra\\-O_jI=sEB<62G*8CDR8-\n'
                   'YEMA3D_P>d@EWLt[$3Qa>h`AD(<cDL^u8g9P#p/St.m6l@Y.e5\n'
                   'PEB8E>q@U-\n'
                   'hnH(#Pg79Vd\'JtO?L4P,Rsjk1ECPZY@a/^"P(3fF7W\'/+;kgN5\n'
                   'Q:")JoG(g7Dm/T5H5drb-,)1"4%E:<t/S*RK',
               18: 'GauI4mq^B;(rne@bSR\\sK.sc9kN[t+FA"6\'RMF5$k`Dnh.)+Hs\n'
                   'P$E1,5>mpm%M\\R6o?PDVf5\'*C8Xi[,b^:)lEd;^"H+qUYI)#FA\n'
                   '@d?d0eD^CppacX!F:]L@OFk4+j"$Hl35U\\a*LbP&1RS-\n'
                   "*)Ks/1*S.%T\\d82^5fkCfLgiD9h@B],X21Gf;+&Pe5U[*;3'u7\n"
                   'YiBu#SA,M1C+8?<(Xr>?%XK*#UHNZ[cobD%,Q@XE\\r>J:FY%f0\n'
                   'J[NuWG/5Om45e4"Ce`gA2J@n;#hC=5"U/K(*!U69,Q2V<3Eh1n\n'
                   '[gI_*QU2#7dK)XoRC7u%3]WG`B:K?N\\b(i6RU"i@!pM8&V:3#_\n'
                   'T"QVSc]p77\'$KXSa/]3]^bH4m8!QZ58&A(n*_^oF`b5c(\'))nG\n'
                   "'m3R%SS,h!XPSa-\n"
                   '1r&]dcF^eL5oc:85FbSr^"@17/mUpa_`bK/pB0Io;.JW=^I)I!\n'
                   "74Z2Q:',q,9FM/U#25em@q-\n"
                   'N:.)36Ke[mC,Val7"ZeS7*^eWR1,U;C0<.EZF/gsCmBW0fh<mV\n'
                   ',sm@&GN0iT09H&G3W,(r^D`6.h/LU[\'!sBfNdf7sKCo;O;`Yb"\n'
                   '"W)_FZ:m*7AdW7`iD\\&:4<=&TTaI$\'$%@Fi59W2Aince+&(+p"\n'
                   'PEC/_f3lj`o$.$\\Zca,JuCnNm2ChDu+(HaTBZWKJ5+"KAV*Bji\n'
                   'R',
               19: "Gatn$hi#rK&BA(XS.?'Q4p=C?Je-\n"
                   '`6lghARqJ[F1MJ,:P"<UCl-\n'
                   "C`b18R%XTGbC_uoB,iJ\\kPoRCf6adb;WriZST4c*B'B/2h$*8f\n"
                   'CE]!DSG(:GXBXTU&A;:qM\\-\n'
                   '$#&MEnFMg:!m6f($\\rWi<mFbOdEp27A_P<1Po*7iR7l#3Z;g-\n'
                   '1FE(4JL3^,bCdLJ(%jJ*dh%M2emRq)dd03QHpCkBFki$WtD\\1[\n'
                   '`)K)>*CneFS4aF3ls123)3juET6Yq,EhY=r+S)NZ<pp;A#6UYI\n'
                   '>&B$<:+/=#3M/$DbLH%F5>Es>56DOCUf;peW8#L]+9k`+oUO;l\n'
                   "7G/4e@*hc(*QDl[%tD5m4)/UB;gQIg>YatWS?'!+`5cmG6_Y0!\n"
                   '\'2[P.],Lb%ppMT%XFQG#OI@k".NL9B1kPu%VE(t[ZjY`;*+;`M\n'
                   't,(V]IsW1tab4&W,<3jL5$H&kp=C/lERfiP32j6bR(Hdaqp`Vt\n'
                   'd\'\'iW=qX7iWo&sW(h2<\\"%C/smq"C"Y9cEk@QgS+jtT;U`6`Uc\n'
                   "&1L-n.n]c+lMIWh/3Il+9LrcWlK^'2Q;bIH65bh2ZBfSQ-\n"
                   ">Zi.u<\\RgPfm;Y5W*Rc]oL]t'BKW[D@+sU\\h(qL3<%*us355bT\n"
                   '9NRtf',
               20: 'Gau1/gM>87*6/M+kX.[&#mlVYL+h;o/8a+*lp1kDLMR,[nSLme\n'
                   "SLhb:BWH$DT^V'gj8Wn`j<WoWbKt[([Q0]3q4-\n"
                   '@<SP/Npqp,B):@bk!n"569?t+7q"P*5YYYP,8c,a8g#TC-mfPq\n'
                   'D5G1V.Wg$Y!O4mMaB[mL9?SkR/QOnE9oXlC>cq)>P57<!&-\n'
                   '03/A848#LZkV(;$[/UO45k&Z]N\\8[br"#(5-\n'
                   "rT/Yau,'`=DIE+Aa*B$SRqpX7<o3<==@q';NoF-QJO*peX3$6Q\n"
                   '$4WlTs_FXM29_^U32bgj2@jXrf`R<.5GU_41s2c<K`(c`O,gt[\n'
                   '0bJ@=q+)$9()"@\\`YDr3YHBujT+7H8#UtjSYgq[#C1/PX2bZA2\n'
                   'kg"QY7L1@^u&lQ#L:rc\\Il6[P"%!*qeSB^6k24`7TR\\TXKdEs6\n'
                   'Qkh"N^YgC:LtC,3k1-\n'
                   '9<b6$P"=DM<YlsY!.\\B/)aHdObUiM2[\'eKAYdW+2TUV;U_(I]k\n'
                   "7&*_eu$0W+(g`d\\#4'[(d])!uabZl&pRGMq`aGMlY!k_n2]rU]\n"
                   ')]c2e7aEcL0+;7^\\TP-\n'
                   "!9cPFi'[%BnEcZj)pT]eW`I**RCZ9)e97mlf$Zf-\n"
                   "l?OnGDED,:'3VQr<a9#.&ilA2fD[DM%e&q]CO-\n"
                   '`C12^9N96_.&ZFgXe`3Nr?IJVm`q4/d$!DA^R@9;dltZ*[P-\n'
                   '+Es0H@lQ;<>+X:DAol<Np7Ws0e\\^a[&fl9YZqd-\n'
                   "7\\TTrlkn9d,SHFCdscR3HACi0s0]NY4kWUtq.`'GV6j]m2iF)U\n"
                   '#kG,/.+46/EI9pBtB-.7#RPIRUu7&qhH(Fj(-a6]3l-F-\n'
                   'p:8gbL`,jn*<o=f0H$SongI.92Gl]%:MT[(NGFSraG>SUmq&[R\n'
                   't-N$+)_/]-\n'
                   'NlO$H("Ws]5kE@]$teg&aXEGoBqaGA6R;CR1PMEFVV536oG^NK\n'
                   '`;Bei@IY7u*b>R<^T/!1>F(,H#_)"mn\\K9"g\\S-"u-\n'
                   "8GKoP5+<>VR&X4mp2,]'g_8Pcc:URf1N9oIeTk=FL%c&0F)2Ql\n"
                   '3JMi\\U5XWY2%-H2CFDKapQ(o`C<jUuPs=*V-\n'
                   'P6.`>;rkCP^u&mn9npU9#SA^AGa19N%?:L6(tkR?mF>96oQ4NF\n'
                   'X2CQ=9sH-kj0kSK#S?qkKB>r@5nb:@((M?$g5FXeLH&O]J\\O#>\n'
                   "p/q''W`m919oEX&caGLO(TsnS1cIDAqB:@d^OfVc3CU*Y`&G3r\n"
                   '&-\n'
                   'Z\\rVjl^Jl*A2IJ_H6m>a!dKq6E$(Nc5Ije1XYNna.p"5aVPcOW\n'
                   ')[#XI>A0"q5aKRo38kkSR0Mm/Z',
               21: 'Gau1,cYq8d\'ZZ%Y)M^^4VkIgq>f!*V=OUVkg\'\\XO9k^S\\1^"US\n'
                   '30#dbrK/QY5:V3eGMdX9r4+d]P9s%&`drT.qUb?1a3SY[pH--\n'
                   '=+5GRtRf)S"rBt:sdfuth@2-\n'
                   'DjbI*%P%/`rj[bBP<8+.9jOD^#gSPc;??;H)1Y@]b%aI7Bb)N<\n'
                   '$)]HRcd]oP?tM75aY)rTh@@_VrV1<7Q<pq\\t^dg9?t:O)L6^&b\n'
                   "u#qV_N5`Kr(cJ>m7&jU3d0^ITph'bk[1<tMTNTjjLeLFXT?[n_\n"
                   'M1bGj.7?TC^q`%#7&IkO(X)jTB.[G7ieHN%.$b98F>2CgnBaM%\n'
                   'gh^\'Z&`\'sUN#GpONAneEF2ENL"=,gpl+i6#P#m8k2XNn=b`oh3\n'
                   'r_d8F;28iY=@NbuDNNq\\L/bBbpaOs5^),^Dp_,_GBO<G=kWlm_\n'
                   'Y/8nC/C^jAThZB?)g>)o:MnHnZ-[eg;1[re>/,r]*V8@4-\n'
                   'p*t\'YZY&6la@hhjTK`jDj)oP"*cLa(PQ9V@u4\\Moe-\n'
                   '/cpKmQGXoL;!&9]aXYSdu^<n0BWnI`g%uh]Op2dNI@7(B.)/DS\n'
                   "(fKNd_ImcpS('q.f=6PkFTG;kr:;8l!j=#iHURE3_49dAKJ:sN\n"
                   ':Z[%-\n'
                   'I^;n[o!]K1)_9BA3i>9Or.UOs,e&h&\\c9Q6=d?VB:b_MB<FrTi\n'
                   's#d\\$\\aYrHFN(![V6YihfnE.0aP2a%X-Ql3O!U!#KG-\n'
                   '/"%0Q=OS4$uDH!Ri-8>c!ckOS;<cIm?FR/eg',
               22: 'Gatn$d;.3-\n'
                   '\'ZQ,5k!Q`r6m`3"W^EYB1qDk6Y(@EXk?&+difbSNc,gTa1o6&[\n'
                   'JqC_o2ihnVZ)1*V1hjP<\\pPYH-hj504!2R-\n'
                   '^Ma&L[rj8`pA(g3Hio.#MS/f%!qK529aCMs8%p2s9j)1.M5geK\n'
                   ';EG6Qck^o]8&!gN!hX]aEBJF4ha_!mooY;_lWAA)YE//`55pO+\n'
                   'Ol$H)p_ihDP7%oKW[?`BGI2+aib302V3uE!3C-\n'
                   '3@prinn<]sG&XfiBSHFWN_QG%_j7?lsu(?WoFEAc/@-\n'
                   'TI0OF#=T%O-j-7b7\\HFY73+3_IU[Pq-Cj8XKYj/n9,f?+;`>HX\n'
                   '&!GYUoU"p[!K8]%I6bQ;U/0ZB20(b;Y5?f_Rd3]e!G`7GCcIGl\n'
                   "PbMJ)``X,IlFF:N+01*Rko_)Z@g_\\S.\\';ld?2HG`E.GbK??XQ\n"
                   '2KIgKg5>&5%OK4)"IeAZP`-tO.tiEDY@ZNH(&<!MtWL)@.t"5-\n'
                   'mMhOH9&EXAH\\^U:KQqIfucb+q-\n'
                   'LJI!<1odq^cVf<e^#7_=bgs=/K[f)hu2Nd.I26R@j2DME?0RFe\n'
                   '.nYp+Y]l1QNC0A/MbT(FLPtH=%!MglV[>OMJ/Mi^?M&H/gW`^m\n'
                   "Q636RK8%b[ulW59L`#_m'lEJVa6l4)jS\\i=d#>D(ok$W[N`AP+\n"
                   'H"Ch8>PU8k]:ReZ$\\>-m5p/#pcXL.&s-bCALe32&\'OS@-\n'
                   'W9a\'Qcs,[]6`rQu\'oQ@"@6d5.LHo',
               23: 'Gaua<?Z4CI&AX,\\1`f7^<RGMI0Fo3_&F-\n'
                   'PHbt&qLLd)R,$Bl;oP<d2`/ksl>WTn;p&kMN[2i_h!#Jb&B-\n'
                   ";HT=]WB`)^%;'to@_E;]DD-NdZqpeK4!Ac;s4lh7p\\1EJ39UEE\n"
                   "LVt:nmthYgsS,=<AP^0eSOGQ6Slf4$[K'IHU-\n"
                   '6*#Y<m;*l*j?,AQt/mufI;KR)pV&3>CIkm$I4!+k3;ZNC6mq^b\n'
                   "i:^,VcQL4!]j%\\Q7Gp]Ku7a03Q#KH3;:LA5fN*dWO`'+bT8pN#\n"
                   '@/EodUR`QP\'Ebl1B@>ks=bq6,rki!McR_NhUi)7H#uegj2C",o\n'
                   '4LdR.aH]XV[XEWO;F,O)h.qHofU,1=Vt?X[E)qdXt"2HOYWXU*\n'
                   '&<E9.WE:TcP$]>^&4GR@#5iml+iMj\\8CrbBG3]4*ddi:qm[?br\n'
                   'u`hi$#!7@YN8>T^YeR;Ff?O-\n'
                   "C6ZI#)Dak<*7bP9kPnN@E15QDYTl]S]TF$KoWpoOh6'bd7\\/FL\n"
                   'EqP,F"I->FH2GB=fA,WJE]sFg9-\n'
                   '%i@Yr/d)ZW:DG#YV3hscg$$lKkSOr/;ft.\'Q"A\'@QJs*M/H$`H\n'
                   "3N6c/6+p<CAYN0mjc]lX501X\\M1'+WQ:@iI)ik.^ogk()A)S^7\n"
                   'IY2+fli75*u[oeF1Wm9THeAA]Mocm>ECsQagG.lX#IcDiVA0`^\n'
                   'ACS]o6^R[:5LsX_,EX$sH+$^;2dt@\'b\'L"5V)$"0R",tn)Quop\n'
                   ';;.8hd^*EKFY"]"J`,\\jV`$hH9T"fRN)T@SW(O/l$*ADV;Y<-\n'
                   'j\\Yc.fGQ=GNC)V\\l;?8jE0W"u5,UZl!"<JA$3f%QF(>*eT,iBG\n'
                   '*YCVKmugE%@',
               24: 'GauI4heNlk&BA(8<m!#1LJWd>%eQHP-C_X.EfH`SU.(N$W/lhk\n'
                   'V0d)nP7()7p-I("H#rn5^#-<2QVdS-\n'
                   '9K&6nREU&%p7&[$GQ,>/\\Wsi$iSKrOk@^[B6SL\\1DB=,I9A_i*\n'
                   '&GDLIl.R/9=jAge3CDO>>!;KU"C_&4)-\n'
                   'e`:\\[QB"e=t+n@HY_$o80rp5PX:ur^=7:XlC5QO5<,CTeNJNj9\n'
                   'H$<\'?28S9a!2\'M5#G4[[f^B1m4!(e\')%7!I9^br[%a<1>PP")_\n'
                   '0sEEik!=b46,X&\'^h_;5p]0V&kHqa;@?5jos2Qq")#La-\n'
                   ')*J,[%O>7*a8tJtU=ab^_f-pQn?,eD:3DDEc76K9j&3Q]W#G/O\n'
                   "h6NP:M`uR/)\\W4HO>Mf%?AK3XhiBPmf7(1FH#LV'nY(C'=@Slh\n"
                   'fSp"dPaP&_*\'cc!i!N!*-Y,&QJcLL9-\n'
                   '0Cs&TcMFdnZa)+(Hh;RW_jKd7;PBr2poYDR72\\Y<8*NI5P,_7V\n'
                   'EuL:<=ls,TRSWob@\\<-8_Z3,&S-\n'
                   'KSiR=CL3>n=,;7`.Oc*9]g<=mh28E6UJX+$=G[s_:&$h5^O-\n'
                   "[tZg!E%f'aA?3*CZ6'i1CS4J'O<SDD)%[P0q!(Mf%MG8s@Rbq;\n"
                   'KMNb^?6*B;g`\\AR*SIbtH:B)B%&1;E;T5r@o\\-\n'
                   '[qCBb]Z,+i_tUAD!pu.JNr)DJ@V31)Vb8lq;0ZR',
               25: "Gau0Ah.mZi&GNEJJdF^EBqZ'nZq+,Pl$]@A/h[utQJ)NNMBF=Q\n"
                   '\\_H_Ma^)t7`diZTn!iA;lX\'"S]6b@XK4].JHS]_!^R^qOhp9P3\n'
                   "&%Cu/ILW`.9tlc&1/EFchY75Ej2l=lV\\n'pDB0\\IZ)O4`-\n"
                   'IOt=bNtX6FOLKgPWMVH_YfiS6KAV>O1toU1r1u?U1H;S%M"T\\L\n'
                   'ERsd?lNT<Tth^Si%aKV$2fOQ?gn0MIBJ>9d,9DN*IqMn^V[?r;\n'
                   '3%q)JsC9hs!UgV5S?6/:kYMdLk:1lYCUE.^b+m3gf5g-\n'
                   'P3JCc"3$F7=k+_=T6S)(>a-FK.an)p.Dis/B96Z&-\n'
                   '4pWdEGK":pH/fQ=\\Z&^?kGojA3OaF8f7h!_mC4W[[LPp:o(D\'#\n'
                   '"(h:S^!(,:XXO2Sn13We6,*]@9eF.or+jPRJ$f[R(I&Aha9I$-\n'
                   's)UVk#o>Y<$[`Bk?RVM*._Jkp\\jq,1cZ8e\\.k]Q6(r^&d8UK(Z\n'
                   "H&a,Y7PZ`e#M3S:u4/,Q.sK0e@[8_<<],/Jj>TiKHkE]GD'-\n"
                   "%'jE;FKV4k.G>Z<B^+4JoV9UUf:9I'D5hb62K(Wc:]J@>1F=$W\n"
                   'J0n-\n'
                   'YS<?XhX8e=%n34!*Yo/G<FT8^\\Po"!omSKTAWbJ4M_oFoJOB4D\n'
                   'pp747JtG7ddLS>:JpL/SmDJA$mHW%jnaTl:q9:"4."7<$aCk:9\n'
                   ':pM]jCAAIH0Y7S=F""H<\\1.@Ps(`];Nf#".[b+J6FPG&Z]J(c#\n'
                   'RHLdmjg?]%UK1*6m1:)J4s9&(ci4K"][Vh@ri8DV0!n@;nCZEp\n'
                   'uR3*t>onVLn&%"0fhD0r1HUQ_iHY^L7"GL/56DHlT#!QKkRFj%\n'
                   '(Hm@K^4Y1ji0$sJ,]50+dJ',
               26: 'Gb!#Y95i9E&B:H#*cd\'m9"?\'=7>2)Kdb%=M#6u_b<RjQ<U(Si,\n'
                   '`p7V\\ig9"+9+E)Smu?H/Z?@/<ELT-e-"!si1E#Y/1E-\n'
                   ')dp#,;f`I#R:9e7@6#mF^=;DaCsK"%,+D+mfajc6mFRi=i;Yh#\n'
                   "LXm?knRd=n@0'W[iT?u\\`QA)R/=nL3BlHlBhj+D*u#68i)2@Ni\n"
                   'Z8PN(OBL=F73rfJj_b9\'X;=+9s6Y,SVOSk6,*G9Fl`0(])r%"n\n'
                   'i5CC9H-\n'
                   'Z+_jAn\'Z!B+cgD=0Pa\\Uft1It6d^g(\'ga_<fm.V1o"7$XS4>Ie\n'
                   'G.kcHNBK9b[H6b)hNR3g,*PWrJk%+k^+Lik$\\+T-\n'
                   ':^V&0rH@9b/gZfro*aqQam94*lLeL"2n\'lM\\WjUU6+,_\'1m?8f\n'
                   '=^a5)UGD:K9\'51aUT`jbFA3cS"q?i/K)3.8$CB$"YWb;EY*9oZ\n'
                   'p/QF>"^5!GfCp5gR*4F#romaMR$lNldor?pp\'[C._4g^S.\'aiB\n'
                   "4#T0]O6>kP:/.J,hV7Em7*JjHbC'`XFSt!<IHFJHpEMWbB7m;8\n"
                   'S:rZ+ni,C:I2Bon#el;8"@`\\?0/P6Q#9JXsWER6l$Vu;56ReZK\n'
                   'T+IOh5l_<RoC@[%\\1J`]O8pFH9H\\Mp7A"qLs7=n71U%6-\n'
                   'A@X=)i21K"-\n'
                   "56N\\'N8qfa+t?&*)],c;$NTagiE<$PCtX7!$__bau)'ZSmmp1Q\n"
                   'muQ^:_Fc`_&:9mh453j@hpIB"8&?\'W>]iNM-\n'
                   '[gH_bQO9N_S8gBek*XbH_Oc>:t&8,)Zl]U<W,\'C"Q^>X,#p(Zu\n'
                   ")25h<UK)l_`aKr=>n4.'N",
               27: "Gatn$h2B`I&AX;!3$2=]'e]8(c6:&qP[9ifl%]dMj?2KS*-\n"
                   "`TX,+E+a)_N3YfsB986/VF]nIP4U122qW0'Uu=R;>K-\n"
                   'G@l:[g$\\dnq=Ah)hY]DG%mSG0e-\n'
                   ';b)U3t67]Hrc07XTeSDRPU0m3AI,W-\n'
                   ')dR_mV="3cHuHn`#bO)/r%I$8.m$ApaAc:^:kuQ?rX5!2ml0pJ\n'
                   "I.p1'peDSe-\n"
                   "[;aTR+Ri@k+[i^'N`YBUW86@+Znr'*S?f>oE\\Ug2EsOCEk29jU\n"
                   'a1&g46XQ&)-\n'
                   ",/ML/POZ^N]6@+>PC4r@BXMu<b)38eMMD81R<#;f'@`GjHZO!W\n"
                   '1%GBSBa[HchYZRG**1:q<MXA,MP/Y:5:09QeN\'U#\'YX"?DZ\\Ec\n'
                   '6OlL3-\n'
                   'f%*,>&<p,mD$\\Q0gW5uKnrIB5EBOt\\Z5&"^eKtl7A+m$[dISZi\n'
                   'rA89*-\n'
                   '6#6Ab4>SUHBQueQ@"T86dF;hrP,?J8Mqu;`QGI3gB<uK$=56n]\n'
                   '_:@B=rQM2/2Y[^bI\\?c@Y,Q&H^VE,6$7W[jA1^ss4mrup=b[4+\n'
                   'cYX]A:SZS8L:Ae^M7r:Jq=3\\af)K.@]Uj90m,U.G&3V5DGcb8G\n'
                   ">2uq>Qece.65d[e8]ZWLujAhka+4/be,Hnpmsr3HNq'*AK/FaD\n"
                   '1h)":=S4;-\n'
                   '34?5C6<Wm/_:>3h!JKaL$NitFZ0!RHJf@[W=MosGj,.rS:usLV\n'
                   ':Q\\6`91!!AAgFD"e60KDSqn(?8_f$>YaaG;-\n'
                   'VX/K,V,#F^%JQW@Q5rg$3^,L>!l`8d7bo8"-\n'
                   ';eWWqi=b!9m5W^6rth5+:Fm2HsaD#=Bur!sh',
               28: "Gb!$DcYq8d'ZZ&21_)N6&cFG@JYaA(#^,sN-LG@Z^BT9^8F24q\n"
                   ']/Xq&gJgg(O\\(bpmMh5e(WU[PUhdQt7_Z/!@`NqipRK1:*rZVX\n'
                   "+,FF!4o.i)aV\\/%0_L)3oENXi+[3r^RYH5ug'<pPF^?5de$H0J\n"
                   'je+7/@+s@KqE.%gOs!!%\\k:_mC(i^fJScLh#oVY=r.,[!i>U>a\n'
                   "Dhi88cVLG)!EJSaKJVD]s8Re'.0u=3'r]-\n"
                   ":T0W'RV;C1!9k2_CF,3M'\\X;qcd(#h<M;$uID.H[K>-\n"
                   'uS5b"He9;T:T_T<#em2AGSeU7ZlmQS.H8/5)C$W%NFdo%GQikQ\n'
                   "QjpJtte#GKL=f3<V's>@Yb/N^/V(2f_$`i6Z#H>2[Js/*CQEFd\n"
                   '^W5QM6P20[s12oX2iGasQ9I!<jB9Y.BGaHf"?^p8sOm2A<WY&Q\n'
                   "_iRj5(MK.m-i/(D6kq$8'jn-Rc\\Z%2nbC4mjnDP@,W1N3u?Pe+\n"
                   ',!S"fj-=4"Jo,60f;#o]Z]Kq-\n'
                   '23<DrB>&F2KJhG^/"&kM$`RZ0$R1U@\\"_&;6r)R3j#R5r=BfnR\n'
                   "BP<9sVCt5POMtL,%]NR#Jm-SD]'Z;fm0p-\n"
                   ']$NAmom?,ULEir*_)J!V9q^NI39rXBoH`X#4D?:(@0_(f5LgVE\n'
                   '#aL<^Y?.I9WZ$PZ/sqC,OesYa1c1IL?l>r2JkPF/E<sEqhAYdf\n'
                   'Z\'"<q]GZ4lQH',
               29: 'Gaua<9lJKG&;F="<">n/<(0eI/HXFR:u]e\\ab<8#<2be0";`=I\n'
                   "['nSo7;YP78m;TI\\Bg/ns'fKYp=`8l;_t]=)38F%I<V7\\IcjeB\n"
                   'FmIB:&FQ.\\0Dq??@ta8SO4,=3^UDdH+md>)5g]e9X:Ck"GrX4$\n'
                   'M5o%V1Bcef$7nF6__^TRNl+5!SO`D:R\'P)4G\'"<KS`m?bL=,)b\n'
                   'KMK>F0uDKr$i#\\*nL$NrJ_q#V-\n'
                   "ZT'7LWL@R6hIrKB09V4ao;<9!9=JMBoQ+K`HX2Fib`4>klYIJ5\n"
                   'U^q?X]BjRN&NOChI[*;IIq\\uenmgt44OqMF9J=JHN&_GZn$)@r\n'
                   'SF>olDb2$!huhSk\\X.joNFi!HYK=[3<tY4Kru:bOXCH8Rq`]Q5\n'
                   'b=^s71uo%]PD7>%e"l4X@TB!5R(=i&36OkX\\t)5jOhe.P:+D<k\n'
                   '=INPYuZP[aEpdBk.2,U>C,,KY(3$u)C1GDXQ<MR.[=Whc`oe\\d\n'
                   '&pZNX,P*0&p6&="[?Q4O"tX2H!WMCU,"5+_)AqVD<d#EZhc<tc\n'
                   '9X7q:2o\\5"QDLe:oX:MhVK0&SQ62EC`Q=KfrjI[?uO&;BQ=!fF\n'
                   'a`$-\n'
                   'iUU"47^Mk@0(ti2OF$/oZi)MfTPVHD`tpkkW<Bts8`>jC9V%lr\n'
                   "`gWaGb]F<Ccl!qi]$3'%)ik]Xd^e_E`^k5gKA0nV1b;Rf9r8c5\n"
                   'UUmJC\'O5,I2\\"=(Vu',
               30: 'Gau`Qh/Car&1=4$G_d&FW1$gq>X7%)X]sMd>uRFO$,M:f&e]OW\n'
                   'i^;#C>cg_pUt_7>\'"n+$j1jN5`(liR8HXdHoiFYoZg[h`h)Y4H\n'
                   'mH:\\G46^[MhL"WqGuJ5l5h.[MTk??rZ#P_RDAqYGa#r],h8)91\n'
                   '"s^H9lLrSo1!jdOd%:GcMPd@qkbC/I%53@E)dWat_TkR`BPiL!\n'
                   '"R,\\2Sp=fc_%14-LT`u31-\n'
                   "L#8?1t2=,9Z:=_.+I&F8mutWdG#F8`8=.XB'#B'(Qe&MALDXI@\n"
                   '10=U/Rlt<-\n'
                   '\\OUKBN_k7[G7hd.usfbU3"aBCZ<8CNZmtd??&7KMk:LXtGG;/[\n'
                   'M@t7EY9KI81s?qb)KuA?2PM3>5,3&Y9JW,rT9tQ!BV=KMSUi6(\n'
                   'BL8I#pP$rkK`@U.Y;!i^&hGbNMs2fO23rn1L9l.\'K:!Mai"Rrb\n'
                   'PDBO(HoGnrP[s1n3hpPQ!d&>$a30+HH\\nAEA#>>E&kfT&s[e(Z\n'
                   'MbN<UjJjDn1:e.Yk7LD9bT1=nr22:I&KDcYj15eX7lD+\\etuqB\n'
                   "ANX*b)RCjb52)fo6TsV94--D1Q9,\\_i._8'[j>Qs9M]BI0PC&r\n"
                   'W8qCF(Lm$<pQ".Upk1kj&1Y:`5rn>uWP?j/>U2Oo7-\n'
                   'Ep`"jcDlB#TV^KMf;^4023VI&nI.Q.f-\n'
                   "dKX<jt?g$*%0pkU'&qX>iP^[r@Y`N%Ls&A?K7LXc,(tAfrTZHi\n"
                   'l/"D`Si@bDE*ZolN<gWB9R"^c9m8ALKtSuNgJ&[QoiB\\L<`5>g\n'
                   'e!*maMW!2(p@"VoY`IFVJQi\\loW57T\\m*GYik^3b;,&pch@6jD\n'
                   'u4c=^j+5tHUI.C>c)UKf<uY,pT5U_iSZY2!=!u',
               31: 'Gb!$Dhf"]T\'ZVNNbQj;CAdQI?GW-\n'
                   "^*h:r>O[P_3(1tn>!aV's8jMM-\n"
                   'R"j=)gBt$8WdJ*P#nNZRTo9KFY7Q93S?O30CIsoUnbPC\\hpRdF\n'
                   '8l*8:#?B?&pO=C>GY8i-\n'
                   'Xi+R#d(^#u5lB/.h.:#A,5[D(,.Xe.K/k<^#^Cnj$I=dUn-\n'
                   '%*oj`\\TQAU\\A).:=(:F-\n'
                   "Tf+I5)q%qN?S#;#Y4@l?N5[_@#qi?^;1jTRICP'EIB%$@@c^;$\n"
                   '(-6n$"(J^4)H>"J@!?D0!5*%S(a>^-\n'
                   '!$V,Pde(W29_ELU0SNJhEf9/QrZbjJ+ccUGtcJ(Q_C-\n'
                   "#Jn9=PJp..;KQEa>6ZAi#Q0?MdEKu;>C0>kH^S>A)@Z@2If?`'\n"
                   'LE86;LYlBR>7Es]7m`ug7bZgnp6W+Qu\'0[/!\\W;:JhPq"8WN*#\n'
                   '^G;6cV-\n'
                   '<rf%e>O9SQ1sBm3GQ]%Q%?t2JAV>62$4L=:lNWUpf9kh<K(ekp\n'
                   '?OfJCl>,?ho-\n'
                   '$drVuY"XdO]9@lW[(bEp[edYR[,4TB*LY3D)lq&J&GLlQ1HDd*\n'
                   '.W>5W$@Wt9]Oq@T/c#A>/R;%R%Y#LCgZ(<(r)e=doD"uILU6D9\n'
                   'B"f,\\2>hCe*Q)5?OY5Xt)EA"$H3EE;`@?LJXc"C^Y,O8%O;o\\W\n'
                   '/\\mMhjT@U<DO8h+=oJ4FT3Y^pW6\\gCXWf-S#)R[-BArNp3@-\n'
                   'haerS%-KZZDOS+Ff_.t?"+@45?1D3[T-PZA4;+R%fZTc%gJm',
               32: "Gb!#Ys%D*3'_bkOrGYS*TOfh0NW#SMAkZ['.gubP75Q.NY7C!c\n"
                   'ALTKRl#gHDKC/F-\n'
                   'gYVqeeY]m!Z(VY]/t]qkHXB"(a34G6q!Dq$9qO"^H)>K0%<ENm\n'
                   "H5S1*8IWU:$jAuBG5(^d4i_a2]?IE:?)Qq3lo[OX'8Wf#qWgt_\n"
                   '?@Tm_I27%6Ath4r>rC2O&PB;FBS=W?&Z\\/*n/$!B`:!sb-\n'
                   '@3>AXiUt3*Cb-\n'
                   'n:_O>>XIh0H_@Xcl7cc\'IO?8CNc[bR[dR"ISR=:!u!DOi$-I-\n'
                   "=t!kQSWj>5q#/<'i(^5sFuO,r6pZhcVJY.bW)!O>XoZhgk<#BG\n"
                   'Q?<pP>:X+UY<mdcQ@F0bAP_^^Ii4h&_2EZB+u/?J>""*83"DT^\n'
                   "j_7#&7^,L_e+if;AW7[f6.Z_fjjR[0'N'2pFFc3!Bl5qORUq+>\n"
                   "[2ZaqtP<E6B'\\Z&4Z=o?bNj:n?me!]1ppg^FnJ^X,!ALFrg<.\\\n"
                   ';Hir3nE(l"T)8+f>!]s&UB0A>2@V>,L`Kj((N6d+MLK1>`\'8Dj\n'
                   '%)K(J:dGBl>fE:+*J]8HKoCq)gSHS67/hr\\1C:^A,N\\IosDnA?\n'
                   '=]=jus',
               33: 'Gb!$DcV*%Y\'ZV0"eAK-\n'
                   'I,"jT[U^&K:24KT;.YpEr;KZhjKi3e`8b-\n'
                   'I,9JRcZ2<I_KmrRges6X?H]#gg90/bIWP*n8tIHJfBI"+9YIC8\n'
                   'W^G\\rA(9>!V6g2/9Rf.OpE&nMi8M%gE4^"[;j)S4>L!PNR,2@^\n'
                   '0055(d+cXLqXnI-t@fs_94+ci$IYRqK`@/c!;-\n'
                   'JT"+&>8ERd\'Jq5\'[$N6&h..WOT9_RP/$)DTCTT.9<)@UaDH&-\n'
                   'm?Md/:M6UCShg=T!hnFC[m#2C(T^Y`f&lo0R6bL/h,U.s<pe9)\n'
                   'R&c->BQ#5(CVt=]\\*RB:g5-\n'
                   'fs$*>YSPV_%(\'b9R"E.0NR]cp7?U=qCF>9??WqZuS.ZDQ.rK@#\n'
                   'Wi0nRc"l+X7%d%r:tf;;4VF,$H8gSj*K=8QpdRBOWa\\A%RKQ2C\n'
                   'D#lMARo"BEZGE>I)4ZGKKkKQ\\VRn*^V\\+gg"W/o6bm2+g#i3?J\n'
                   '/L)UlDjX#dE%Co"`<1P1V^VpI&,.;"^9;:/`]W#,I!`=q79PG2\n'
                   '+KW%6.^1De\\nE*d!_SXhT-Eoo!47LoS:B;^u?[YH#U+&^Z_qT2\n'
                   ']RQ@o)c5N+`$G;3t]&2L(be-eF"i%l-\n'
                   '+iBsQ^/7ScQ;NKQboLFMB1[Ib;\\Ac9N+I&VFd/ba"&nV\\a3g%A\n'
                   '1om?m7Hs`kGd_><+0&b`O.)Jde-A<-\n'
                   "W)K9(]`0*6$IpQ#?]]['J+Apf0=.mTQ*G==#9dq^?#=/KW`@6Y\n"
                   '7*L5=ZY/VY3\\k+NchbLAX:I!ZO_Uk=/o6h@QhcDoUne<e]T!E@\n'
                   "19r[E%Yp<'qdqLh>@8Wer;r'FsdSAEDWP*4R/ZX$@[EX=Vl9r,\n"
                   'JY%]lmW)Kul48POcUXM(][cFai#;Z<Ao`',
               34: "Gb!$D8WV=S'S)#g)@eo0m7?2&GmF]c0^?#J\\fjHf1lMuE$&Q33\n"
                   "5fcO`,\\drn8_VSp'&7oQr$Qq/DRq.^!k0>5]Y=.<q0@8Cn,<*2\n"
                   "E[Ub0f_oSJ`<#0,BB:'C_](G(>:;t2WD3>cV-dn1XaL](G$ikt\n"
                   'RK4LbS..*K3.d73(i2eH#Z67&;]I1Ji($]a9`<$9Pb^;4P>MB0\n'
                   'EZdW-\n'
                   'K4D+eC6+OuS<ZDt:,k>G66RDE1&o@frSZQm].<aRB7;1VVEEgD\n'
                   'q=YF:%(A7ss$FMcYM?17<b7KpCH<eJ5#C\\2AmVDi"W"#0RZ1;<\n'
                   'M(*jZlrj#dgcNdGH&],*]pr_><`aQ(Vm36R3>RoFnpMKaD,m0>\n'
                   '8LE0DA]cO;XhWctNnsN_m39Tr3)cDe/a^isb>[o\\9:97[*_?78\n'
                   '2_"tk@HmH2D7,n!%:b#`QA[8rmA6a;jU:hJ"g0%>rliNsS$1#9\n'
                   '>Kc3k*_?cU:0$:;HqPdCNj``[[l:]XA$o>90WW_-\n'
                   ';h"Cn2H/K\'S0.#662`Hcf]Wh+h9&BjOsa54GWOB7cCqpRhI(KP\n'
                   '%@?mN^Dc4/U\\VA#-e?i+kq]bo-\n'
                   ')M0W#ZL=f6@@P.;>MmhFI9S[-\n'
                   'Jk!(7;MG9%<"@9`2YddOc)RM$Sr]ZkS<k;$j]br\\cIOrk,5WmP\n'
                   'AqAg*\'/urE"gQKq!KD6KKVO\'3_;bnK54(LJ1Nb#0W1*=I%h9nB\n'
                   'aQ-Ta(+Hm\\6s_l@KU("a=qG:AKn$@1_#Xd\\)$=O2UTc%Bm*<O,\n'
                   'GntY8ZQK5AFqpk@i?2RD:7eh/`#D8Du9X,KF\\d',
               35: "Gau0A;/=o?&>!%9'kWXq91r\\-OhJ,+8R:)Ue%f'nXJN:T_Y-\n"
                   "$FCs/,Y@L((J)q\\PFfA!\\445#W7gJPDm1gc&e\\kdOB:5\\J[f'd\n"
                   '8+:U8:Yh7c0r1^88e;>E";hufK%C`#N/pJq1a9L%\',brc$,3RG\n'
                   '0bAq8VJUYetD2iaW"!#W;_6,>MdI;Zt/N8XiWa9D<(Jq5#]H&s\n'
                   'S-4cZ$odKLG<5NA8IQ2ho\\K-\n'
                   'ULSJj=niP.iTD=U^rbLLC74P_Jg.P\'W9J@1WVGG8Y6li05qlr"\n'
                   ";cO#Ys&+G5RPPBCmVpB4':'s&/)=_t%;i8e2=\\23^:hWH_XGB`\n"
                   'A_L7hJ3A331Gi5pa>9b5tYS8?L=0lJQh,A]Ycgp_>41Y:T=B?G\n'
                   ">96F/H7*?Q3?RJTjMgW-#plZWDNC'R-\n"
                   'NAXta"Vj]H9U3Bf/I]k8Namf/aPp55qNH;deM^>cS/rGmU[`Td\n'
                   "d$'O!EE0qZ4MW=[XI9(.YIE`iLTbc<Sq4,mlY_hu-RX&a9P*sb\n"
                   "oIe930'Oh2g>[EPh-\n"
                   "$EB5H)!gis5ASD2CV=IOAoS9'b'D5F=4\\U^Sn9jc>o?]C+75&u\n"
                   "s'J-\n"
                   "RKD\\<;CUR3I.pV+,h>0;nF0B@=X<?,6\\.Nb,igR>Vm]A76*$I'\n"
                   "@O+(U=%1!RCEbONn&\\%!'#Yh%<n^6q0-\n"
                   "U;*\\'me8`pn[78X\\!9(p\\a9@QSu%Ks37D@o*0G;%RaaV^>crK]\n"
                   'U-Ua\\`5j>`GLP>!?L0C\\><I3%-\n'
                   'P9I+tit7PRqf`l#r*9cKELT(M0iiD31g3hP*B\\kW,f"SGnpoTY\n'
                   '@NpgJN*hC?MI(l^"==FP!hC^297GCRj.Fl1@rMD]5X0FO.@:QE\n'
                   ']d!-<;3%',
               36: 'Gaua<9l&KK&;IgH,s<)=_\'/3F)u!1@UkugefY5k3[)"#B5Qa$2\n'
                   ':j1rC,qM\\Y;Ock]B^^<6o`+T^FQHV3CH6+&&</Bpm`[c=mRTFs\n'
                   '+8u&LojE\'Qq;W.^NO`.MJ_/4aL>S+^9M%L"mjS$`WZPo3B\'s*H\n'
                   '*9c*A1[sWGq"&Rh>5k&NaN\'F!3Fa[Gpd)h"HqLKn0(@Sb/4/9!\n'
                   '7qBobA-"ogo)l.H58<-\n'
                   "s!GugtoE+CUr>?7WpR2']&TDgqG,&IFaM8AlN]r'n6s((mlc>N\n"
                   "S>HGPt:T\\VlGKH.4OiQ$'r[j,)!L-*-\n"
                   '2+or2I]l!Xd9nQ#.;P2/3-\n'
                   'pe/A3))G5HBesd,qsF]d[%Fd?N63m7-\n'
                   "N7H#YYD8bJrE76d2+Y#&!#SnNS'U/r'57id\\3U_MS:o@$\\-\n"
                   '6E7j+NZq+WF"9\\JM5+S%f"Uj\\A9:g3Wu+b\'C52YUWM1!^?lKFk\n'
                   'H0.HL3HCfM?U[gqhrflSE:aI"h\\g6>Ok.(g<3#g9]<PtEMYo&W\n'
                   'I%F:LXIgl0:(%icUS2\\V_<`)t)7-\n'
                   'jq`:\'U&a)[O`NP)5T%_m["f;[#YVrXX8IuC)7=ZN2M1;Y*==;[\n'
                   "4:EF\\?^m.DZ]p[KZK(@a.m*;a(tockE6fl2J:+ND]I1^KL2'ch\n"
                   "4W1s]4#KrOBB1Eh`L+k7V\\hB[rfFBl;V]'>ukp*t/#`:Ap#+.@\n"
                   'q`RqbaJX[B/0e>]Ut^=kBT3`Cj^AQ2YXS#D#6WA:0)@LuJg.&0\n'
                   "8@Dj#s+fS9b+rrD%@'41",
               37: 'Gatm995E9I&?a`OoO*kMVun3^)jc.TJg8I"<5(2bZlp]L6JGEF\n'
                   'A_.hh-\n'
                   "F.0hW`'Q4m<roDrmUjsm`&F7P+BUGG\\lb71])UlnBT@XJ,ZT7]\n"
                   '(o=EZVq]l:E\'*Y$D0I(n*"`7BLG^6R#Se*A\'Zp4p+A)SSVG\\"R\n'
                   "cIrp`SMEf&'i9NN+2'ndLQTo#=&@#,W'K$3edobXE6)ZR+G09%\n"
                   '-WeJ=?WA\\kgCXR`gpI]NT,fMa"sg>Y:s:W=*Q\\:`Xh^!98g.Wa\n'
                   "l;0%\\[+*tK&54EndlcrB-hR;>'=/p@/9S3=\\B<a;sV:PLkQ#m4\n"
                   '9POWcSPP+@gB\\i.66jMEK,1;$,]7*lmU]QC$Q:si?EJ0@J]q,[\n'
                   '@3b+-\n'
                   '8Y&fg6Bj0r(B$[V(D$T3Vd%LXCl"L/r\\DL==4st`]*;$N5\\1Wb\n'
                   'LY9s]\\LJ?-\n'
                   'Hb>ee0DXciE)JuO"a=Is4:uq`Dj4pWESGhB,n@C\\8J0\'k[.Y\\?\n'
                   '?tN/1:^L^MFkM)bZq"5LiNj7Pd;fc\\Z2`CWj8L\'Y83eUi`5X5H\n'
                   '-E$Wd.O@3Q#,5+\'\']:hTG\\iESt4s2a\\lk)kLS=6!,"e,bt1.k<\n'
                   'l@HD#%9?;n%/I(++j8IE5O:mkL6$/1/KLOEP02Fp4*ep!Ki?m,\n'
                   'U;UK*>3u8Wjb:4CZIGtk7BmHrEZD_PG(qc@LouUX&O9m];0IiX\n'
                   'e&nG.Q7TPLcGdtbUFs_Wjb_A-LkVj,^ft<OHB""p3bL^Z#pt>(\n'
                   'PK)5"CrL$h^4+%;d,.R/nuf*4F&IfCpW5jG,qn*G+).FXL?g9G\n'
                   '8t;I>AgdfCe!0\\"ZBqPq8P2UFj%5L\\na@0e?PDN/W?t.&&d9@I\n'
                   'f',
               38: 'GatUq?]3Au&AS`V3?K_b?g^Z#gu:s77k[HgV"DW`kTO+AH3b_h\n'
                   'YXpd?S4QYBp1htWIG[!(n)m1qs0LD.CXGlbfu_J)DeEZDhs^UA\n'
                   'I<[FE[-<4PjG#Xm2[!=!YR#Q+(E4Cl)!J6S4-\n'
                   'P#(MPR2K85_r@AYetGq[(Wp4)^*:h?mE\\L7kAuB#Lod"Ka98a6\n'
                   "P$kaMRP8?(a%k0*7f%kL_'o]RZX$q#Rri%miEa69G*Ci@.n%rt\n"
                   'R#2pua%NUt?a[$WpjfHW#4n.NksaKhu1hXk>+rmP`J[bnA_Wnb\n'
                   "+65)AN_!Pco6D'^$925EX-G=HQ#'@%PP;@[)EUU]b-\n"
                   'a#00QE`h)S=o-\n'
                   "jPP'M[m:F2EmGOjq0t4n9tdEmu@SG>9=PJ!P1CQ@Zn2,@ieQ>_\n"
                   '[;0lVXgu91i3AF&D5#%PVm\\MGtI<hL_HB.bbh2;=n1oHdaAXMU\n'
                   'L0Q3*j5)?PrBt-\n'
                   '"\\nuL!Pk6I"h4R:RLLREg1Y7\\LQ3`n\'[_YX%/_[8%Ko[`kY\\Wm\n'
                   'n:L4G>5Uh<Vig\\6%rC%;e2Kt?0.pHMSCm9D"FlSou(_[ZW_d/S\n'
                   'IE.nk16Zi[e`d>Q^"QW$2!h/2jn8YN?1lOlhR$:VJ-u-\n'
                   'R4hpn9lCYL"o6rQ\\^;n<f?^A\'CHL0m2Q-\n'
                   '(!1[mLEB^X#Gg\'`\\s@uU0`$HH.\'fe<d"q,R48S!+W7l,V:.H6\'\n'
                   '"&QcM4Ge3XuN#$nFf7Hf]sq\'b*=D*&6U$,X7e:JJat]HE.O*pL\n'
                   'oM*QnZ7B9H^@RVLiU3@"g[FJUW$[(\\SbF@fMER4\'j8986lT6`a\n'
                   '^5TF=Lgl5R`^TFPB:h*7<3(1I',
               39: 'Gat=ih.tM*&AVR6W=K:E74j<#>Ole<^#l)V_kYQ\\d3@t/?sc<[\n'
                   'Cm%LOG]u02<8.XDhq\'6rs4;XcO%jXrC??Y,fq"O<B\'-\n'
                   "B`*rPiAFYC?2r8AOl9'=iS$!]N('Ybim)k2K`po\\3MkiRGi):i\n"
                   'l1=VK8O(l.nB%/@/NUZX</Lg`Nb,fXh5Lgh":a*YUK$aPY?Dk2\n'
                   'snSWOZbLAdb6*VfTO%MpfiIN5?&Ud@&P"t\'A*89^BJP9q"\'$:b\n'
                   'rcp3P\\2;QMCVqq_$fHg]]]Z&\'Up&I:Am]TKb@:s\\";+:C9:cFa\n'
                   '/N-\n'
                   'l7o(TWffli&GUnE+D3KVcBYkhI=/ndYRS$a=R0fS_.Yh\\$Y;.D\n'
                   '3^#!qbX%Yo_0KpXg0f7fSUtcObGYQcZKF2M+`_P%0l=J?cht:"\n'
                   'lE)"Dpp8EZh6uKZ3gh5gX3i7MBZ^SR5l/e;j01U.96DuRT\'u\\W\n'
                   'FAYA@7YhDN>u\\#YHpgeEA>^)^"W[!=*&t>r-T]ga>2L&-\n'
                   "Te^dffuZG+h;$DPMGss-g5V.'g&Xs'-\n"
                   "(9X7rP':Oo%_HY>WB%MKcUB8tLhZjlePGZ+$DGC'OjD4]bu`EG\n"
                   '!/SFFQM:Xcu<Ka`Nml@B@LnB64`=2m5BjGC6u\\h_)TM(0sDkaj\n'
                   'XIi>\'fTb++c":6AhsIR*h!*JKGW(9ZQ>qC4\\)@liu@5=NC+tE5\n'
                   '(6i^`b!6b7;*0]oMWQ\\1S5GOJ&-\n'
                   ';psaBLa;Rp.GiRl5>`4VYh)(\\mfH,=@0t-\n'
                   "^A8(UEi*k@m0;9pMJC$E3@BXY'B97n(9IfV7Sop#",
               40: 'Gaua<:Q*[e(rdT_Z5s2gG$01^0X:tdQ>W.uN@c[s6l489JpW\\*\n'
                   "PB>6+D46WHY!j,u4uZh5L>UB8C&TLDD>PU'jIM]_Ie.*)q/Pp$\n"
                   'cf)S,f+nnRZ*.t4"u6I3AMNb=DRMV!.#=1jT(UVi792l`,*+(N\n'
                   '1/S8:EX$"D@EjU<q`\\Y^/tqS7ft(P3NP/L-\n'
                   'SIs.JCu]i3/Vm/]CVjAoK>]sO*e+TmiR!Ppip_O\\CdpAQ$T^N2\n'
                   '(<$.o%Wc:gQU%HViO]a2)")GBLd7V.j?g1F!e#^4\\dIE5o=ku:\n'
                   'OGMnpTI;-\n'
                   '529f$W]`achdO5\'r;m&=^)Fk["%#mNETn];PcP&g/GHL$>70WO\n'
                   'p03-\n'
                   "<b,jeOk&Ek@'g@%Kkq1fp66;F&]K<3DA=f$usYoEL!`oE@&E6a\n"
                   '*GIH\\X0G+b*[?>Q+n3fa/f%4-\n'
                   'mr[t[5Bmo>r*/;85ORl;*r"VqDtXmCA4r$"qclr)t1k.pk"P]p\n'
                   '+7\'h?C\\<KcVb?DQnk]"aI`860m[kNB:#H^(:!qb%"`^j6WsR.H\n'
                   'iG0h4=?*srYE(+Mm:!aS/a&@mC6@qU0$BF5&ke_Z-RUqL_F.LX\n'
                   'k:_I;M60\\8kkR]%!7aosN^lPJ#9FMq;kd@)f1osV%tdl)$Nk&8\n'
                   'hJ47eefEqV>[h:ipfjcsES,e/F.bp0+Qq4)EY@:[J>\\(AgiiFX\n'
                   'g*ouMLSVAgS+e77V3Xp<J.h]@TQTddS(?Vl$ANm,5[PbG)!FJS\n'
                   '5%),QS9)HB8hckqfYD5\\>uAPH3"W_f_]W];-p.<+ML"V0l\'D#',
               41: "Gau`Q>Dprq'K0&r+$un6A[dnX=nH-fV415+fiHIWQXt.E$S1pb\n"
                   "Oi_^Nl'b7:;RN0jn+5]:bPX`)ktF-\n"
                   "0g/<@(VdVPt^@Rn6cB+RbpO<(t\\WcrOkktn[M)_0]?rVPe'CZW\n"
                   '/AgRirUO0RldP+Fh%bo#hDta[mK2$;F@.[ht*:19?6p?FdS-\n'
                   'q1HYY>1<M=APQ7S>A&KT,>h+dWVaK`,GBJ$<jMhMpR^RN9@sW]\n'
                   'Xh#qYuMm)O;FE^+`dOVXd6c<PHO,mM<.Y9QZ6u_!Eg8Ps;RVnc\n'
                   '`[c;<=cbGTa-1:6.sd]1M-\n'
                   '\'*OuO4Voj@Pdue!9O"*p.[N_h\'YImFqS9r5"4KBXUnPsOD,4\\9\n'
                   "*<oI*GfA*AD[LG9<B?TG&mJSRh<U0DJ'Kn#aYAU7h.aJ9BNO.\\\n"
                   'F;!!=gOR$Y8aq["=U*_$AFeZOGK\'7k7mE;%MhEl@]K(<8!&=qJ\n'
                   ':Sso*!Or@M-\n'
                   'A#Vc;o]"aC/F?h6&\'A$MWq=9b[i:f?k_YVSTPgGhcB[iAh^LEo\n'
                   '>GAG2.OdD9Wk8p^iAMU[kE3N0Ji.mB71JQY[o>UZo;qt.0t6K^\n'
                   'h&?pW%q`!sCQ-\n'
                   '<PMp=K/++uR]3c.LWgmcWYrj`2ErY.>M3AhFj$i<4TE!4%7*uu\n'
                   '_bd.XB_#ab_t"HCFX9oL$HF[iQi2XqF$mF7\\WZ,\\:QA["]q!<L\n'
                   '8`P/2s&0+*(3I#`E7^]Fk?iLG)dip)eZKSM*BgKTC*FkDCbU3B\n'
                   ",)2'T9TJ__*m:#,!%UhQN_eN*#)gjk.01m)4<&duRR77bVMgI@\n"
                   'rLFBQQIIfPJY&8D',
               42: "Gaua<6''GZ'Z[=bejDfnZH-Te`ophgb*G@ub$cSNlc/:SR(-4-\n"
                   "#'daIJ<j#6jC%!(kN;C5>1sIWQ7hGo*ppVSRJuBiHd']pa1q$P\n"
                   '*^lW1ro=]0@7"-\n'
                   'EEqP:jGu&)=5+PX525>HFBV(TGBtkgGh.`;uZUI(NO<:(MJk)^\n'
                   ';*6<dc]`Eb2:e+i\\dTM+ui1*Q97q_T1?es[bjH%/;I_k(6bEWm\n'
                   'beGj.m0mlV3b)qN=lc[]8Sle:=X&;VCe4:EIb+M0Mg=S(IGkk4\n'
                   'uj;ohMgSk%QQK_%",)4a6$+Nl\'VDFbn0/r8f8WQPinRt\'cjN:O\n'
                   '<?3e%3%MLTT@EHqeENZrC<b""iS79oJ0\':iVOZ9!(W\'`!UYuPf\n'
                   "YH(*7TKHR)fN.q)YOt9RqHk]XnQQ\\S'&PnS+9,&*7W9<a`e]L5\n"
                   'P/2[;Y.&uf"(V&SZA^QoH8F^e?26\'@I@l5M9OU814Z%1eHb93g\n'
                   'dja9(`1.1u@8osB48?&Z<\'j9Z`R49"QYFO(DDW>1HV#*E^MQ"K\n'
                   'kAG6aJ#^;7YYJlrnG6GaDY-\n'
                   '7cg;3P@l\\LOoE^GBE_bn4pV"7D,L8@hrX_uPDgH1s-\n'
                   'ZZ<2t8H4V,]la,pCd9m+6ihL_bpO\\lBHfC9eS#=Lp>J")7koiJ\n'
                   'b*hd-4YFZt_HZTZA=GDU`g0^#JkHDsa_\'0j8"Tmg>-\n'
                   "UVnV$PLJ#(tQWt'@1%80uUVIaLd1:4'&Zo!7WnFrO,#HNIbXYQ\n"
                   '=GJ#UonP8Zq\\S!>dnSCSX)F7_nJ4:BEK6lE*KifqJVh7n:U',
               43: "Gasan95i9E&B8H8$F1DC3AfhS'g8?hV2cSZd0l3f</:`%'nHpr\n"
                   "cmE(3>o[eD#:1!R+Kg'$q7kQRr)h!Ra^jGfaZR<9As2u#p%Mkk\n"
                   'hYbo3gDBW8G+bsY-GLcBStkOdLciW/Y,WSQoOCVG3_,id:3>kk\n'
                   'CW"m-B2:2F"N-\n'
                   '$n#6JAH@io;>KFr7@Ui9fK"<8,e,D&(nak>eZ9mt=TT;)]6TIK\n'
                   'oY%tF*kS8CZ?I`38RRn8Z$Om`o0IH*`;M(G1JCPs*V<JT`cJ2?\n'
                   'GQP7!MF7A$QM/GR1^M1nMspgP%TQuit5C<O!rAbjP,Ek9H>MPu\n'
                   "H<'J,DI9-\n"
                   "Yk.kDkWS6!$]1R.NRt;;<nJi&T['@gNJh*Uon<<PYm/h%>(%Hp\n"
                   "q@9Sg!pT$W^Dh>4*i'HMXbV_FEC_KY(4Kfq(cj.15WZ`NiU@3.\n"
                   'EfF?Y*,fQ_I%KW[56X*[qn9mhQ<<g3a??0k(H@@Y]b>cM1Q,MZ\n'
                   "7/EY.i+k@FAe[ZX6dtUs&<GPh!Ll@pm`afJSP:64peJJ'FN69+\n"
                   'I1;mQ(bMHC<ipPsedG\\Vbr0T+\\p;H%s#CaR^^`Q"MOqH_k+Qm"\n'
                   ']sOUO6/@%ORF17pW?]M:e`8A&s,REZo1/%0F)9(?1>7!iu!W-\n'
                   'tQ:0C,#@:kGMsNBgt#6mJp%]2g\\t9p;k6knB/0&^`WI<eCgA1V\n'
                   'tf0K_&F:X1o\'P(BC3^ZBS\'+5R=U:$M+n9>Eem"@N=W:&o+91qf\n'
                   'E%X"ZJET=lN9R$)K?9@OD?2JIU=A<%kR!*oEGkOGSD9E*\'2/n.\n'
                   "1/TZid<q`TjtqBIDOis*fd+3'EV+<>RGT:#AE1+5>n6VCcB/$(\n"
                   'J]U-fIim<_0+rHi7O1l%DhI[$t"dRBp2&o]\\[%o>,u-\n'
                   'UX_V)<Tk,(<U%LIHWqX)*]@H6>F]E9e?0bt;l6-\n'
                   'g`>:jpK2g(qi[%;%)eXjSZhY[Te5:WT',
               44: 'Gat%!95i9E&8"@-3S6eELItR#<kol7ON*>D-\n'
                   "/(mPWmX@'Jh'0WGhocjfTtn9E^56RhAH4t^C\\HUgCAma)=>?%R\n"
                   ';Z]M45]N*qL*H5r&+<K)u>7@YbhF;4u/"&&SEmG/cgFV;9reG9\n'
                   '^*t=(@LfaW\\RI/r-\n'
                   'e^[o@h^a`a7W7AZnV_CdotgngIh+Pr3($p$g,o9V#YK?<\\5]CJ\n'
                   '3Z3^lL+iP"pf85N19+p]gY6YRdA!)>lL@!_eEdd8s^b![0?9ZW\n'
                   "\\35'SE1,^`EW?EY/3T1glL$M(F^rI`-22O$q-\n"
                   '+ER]_pk:I`e=GW4RG/DXJ86=>(_D0@\\I<o"K0eY8G7O5jr2Fe.\n'
                   "2]EAjf#kgIK@Mb6;)`\\[rG%*C;/Kn7)/?Rc(07KZ;8]'Ja`$/,\n"
                   'S.H=&Lq2`ooW[(VZE:buIC7e4WmGYk.7D@2Z@15!<JYO$s*[NZ\n'
                   "oo1a!<o/N_l7UiouMaNV1.d',LjfY&'F8uD_mnOj.SjCN`+(%F\n"
                   'e?H=79IL;3XoFd%.+mOcK/$ct<Fh+eeVLf-JSBmBc^5I7bEY)C\n'
                   "L>=d(3Sj<C,\\KN^:3#WTOV6$fJFO&8RpA'U835=V>/QD5\\hUki\n"
                   '+5<m^l29_\\Md[aaR6`E#X*1u\\\')QWDg$!l9Qk)Ef:1Qu#AQ"AS\n'
                   ']n((.C:2ROID0o%Lb/1Tf;]#<h?COtGlt4G+kMoe3j/ME%4Js.\n'
                   '%%=Iqg[</W]]5-\n'
                   'Ek/PN6O%pYT^7AsuQ9ZNhf[]R?0cdH.PL4J0(NK<tZJ9:[a:Sq\n'
                   ")loa]A_[l`*H!M.=qRJ(5\\<A_*ZVm:+I%FS=54fq69Teat'RJ$\n"
                   'jmpsB!B"(hKL',
               45: "Gaua<>AqtE'ZZ'_1`i/2!FkEuP:(V-\n"
                   "?u3NRm3K[s`$VikR`#>)'66.3Ng<>'Uk;8^_7SSaHp^('DD$s5\n"
                   'AX>?%lI`@hro[qk[--\n'
                   'WCT>)oNim.gYE(hpaK=a;)k`esBN_JU_#mg%NAnS$lfkED"`YN\n'
                   'G1]:JY5]8KHS^n]6*)>c&*OcLaGA(_oCYS.E?<]kLuB&8p&!2#\n'
                   "AC`B$1oG)0EZ`M*a<NZDQ_Mk'rBnWX/R.+SOmL#@VRMg9e1@@0\n"
                   "$BTXt\\]8I1!b<t:'[7q;tA@Ik<5!.J;!_\\m9H0@uct6[(>hI=n\n"
                   '?9^hU.=ia%m\\?&iFTg8d;M;aDURiUJX"I[I0Um1#lV.#t/P%%g\n'
                   "F`0-K:!jdDU@N)6ODO,CUrWA%<$j-g'TgDB7(ZHFVlrM'u-\n"
                   "8dWonf60I*W9_o<8.o3Sf*_@h,fJsT6ac#;78.:*SY51t'IoA6\n"
                   ",nR]C'.<AifJ@5EZl49rLapui\\9\\d''ca6U.6L&VH@bfOWtuXa\n"
                   'Ib];`H(M\'>V3d!Y!kklc^R6R\'>&nd>6+Q=R"ptc0hF!P[<9mdN\n'
                   "&iXb<l$C%mDW@\\:I]a]Aj='2d?IA)%1Ws1EnoM<tiK;VT=0tm-\n"
                   "Y$F:A3\\'ru!^elX\\>MgE\\@)^q;Ih#J2!$j&A7[NFR_BO6#1q^`\n"
                   'LtKcmZTO:j2(Q2FOV*lYU"#3pOgjl<N7-\'8gttcI,?s0.,O5-\n'
                   'Ar4Q[pA".el#LDs2i?XZ<B?=GlSH1r9c&*=VA)I!gnD\'XE7P8C\n'
                   'UekApKn[\\\\M9<2Y97Ui2MF1lF<?r(A8`M,-\n'
                   'aZY1:KBHAbsrB\\3O*OO%&M[WgedA?ebTD#AC3AoO(Q?Y3emU0F\n'
                   'ES&96dYZfNr>!q$0(ktV@6)SYp+G0!1=5jeb',
               46: "GatUqhf$st&BBVE@Ln=(#Gd>'Tjo3^TW5B@>2$],',oW4F\\K#@\n"
                   'OIX7WUU<i2B.K64Jp3+hbWisOLn,W)ZF8L)]dc)#`S^Rfde(7<\n'
                   'q#+jq?Lle-Mb!OTpL1BS\\:.%(]LCf#7M-\n'
                   "8\\V/Eta=Kfu\\fr@BPe[<W(\\HsWH_7'nf*!Pbaj3of?LB146KQn\n"
                   '2?#([#&5B+nN(J)onf`D_-JHdhSX(R#;$rG"JJ%17<\\;*E@9>(\n'
                   "0G^'T6q`l0=1+hq9//r2].>l,_$+\\bb87;if1I6I2iBNS0Vc>X\n"
                   '3qf=HPbajj:$b$-JeN5X=(Dk<6)YFaenMQ(n\\&X4d[FXB2-\n'
                   ">+%]DYf*r1,)[;E(q<$=H'I^GYG!@GR7EB]\\L(59c_<s.0LKE\\\n"
                   'dd3dpl6Q*j>YCe-\n'
                   'c8k.9=G^f`,0OQ`YOb9l`jPE.W,)YeEu9UkXNp$X<qB.e<D(pl\n'
                   "2cD!14=C.'b-\n"
                   "NM&juo^i<V'HaYoF,Qs34r12,a]M1b6Ol\\@+W6LQukgre9=2N_\n"
                   't,nqO"U0MuAo=oQCB%Dem(a0tpBr!6LkTCqC>]f="*sQi$V2)9\n'
                   'SkfHP^^LH36I)S+Rkk]]nnU2\\RuoDu3NqhoGk+l/=o>NHRJ2GC\n'
                   '3*E"6p%QG/hNXB47H6C>s=G.)a&:^bB?0.Xdg^0c<mgRSPSV`:\n'
                   '036F"2-h8*P]-\n'
                   '$%?o`hjm08&E,=[;CTU<fHWBX@=<X=$7s2qcc4_9dK%5r;5;W,\n'
                   '%"f?"!uM1XE_?<nIXdfHb_]H1NX:SOkN$/tk5tk:_.j376,/JO\n'
                   "(m%XuJkoAu=-[`QL;FLs8=$6kc5H1e'di2o_@RnUP,(H0-\n"
                   ">GW3,*QYU*='Kh/br^DA^s8%Bot`:Z8:'bHmFIchekAl]4okkm\n"
                   '$XHqmat7_Ea?<-2W&UQgM/Sbm:N-\n'
                   ']Qu3/^*S32Rc&UP%4O:8N%Eio6QA@us0?JTHMu',
               47: 'Gatn%mr-\n'
                   'W>(rrc(W(G*sN4B`Ok)"H$AekT)!Kn:Tqji^T[`./4A$4p%D1K\n'
                   "'gAW.H>NGn9VkPsl@BM2RPp-\n"
                   'p+eooA4,n)p;.naQ/7hpREQijD@MTAqNsTj2/.^=EniM*4_XO>\n'
                   '+7P..%^A4%_f<CdXmo0.D%?%%iuIr]W3qU"(#pL3WlVT+<TJft\n'
                   '\';!o@Eoo<?AlI]a_,^3+*E%#<HjT^ierE>"=.ek"!qBa?f6K\'-\n'
                   'KXF,gHNt$]KYm`rVXs2Q.i:`X!U.bdlYpILh6LnM+)mDLRMkV#\n'
                   "dhA7\\:]b!B,eZriiM3lj':]pc//n2Yih7)bcS#UXC131C996]j\n"
                   '#%<Ji;m;$ou:c^gdAA0.0H-\n'
                   'pMQ,8Z^+4+()^6ef??og:iNTgThV?obkG83p=i8:e!L#KWi"[r\n'
                   '6>>+SiisEG]BV]#[?/ARb`jE\\Pt8i0.`G%1SZkq%3kcMhOGUp`\n'
                   'iiPX3Adn[[!f#5.6WWj=nY=7u"IVf!/]BBe>Cmudj(t+]H)9/r\n'
                   'I7s!sXNu&QZ[a2Ss+nWCW76_hRot6KRD^!W*"-\n'
                   'SogCO,(mmSpCIeDY*Q1gRd-\n'
                   'VA^2T7f1*-KL@h)!!sFm(Tfp:-"rA<riDgnk@pP-HBpiHo;aN@\n'
                   'SpZ][PLm/Rj=74;-\n'
                   'qR[,\'g??1@``V!f")FiD"\'Ir\\qYcXI!hr"DPXCEmR<ueDn75Zp\n'
                   'O%NFM3M5CH+?@Fq)^SV<QLr>#"2"#qO<L_!?:=k5Bukh?M6ipJ\n'
                   "LN3'uJ&#EMsIUlZss/gjo#bh1Kn:')EBIO@(;KM%'!7*Zp2QVc\n"
                   'dW`09=n"lj(Vfj^?QBN?1,b0K*0!+cpL2n%FN]4OU`JG/3``Lh\n'
                   'UkD+db5)H?CsEEH*+IH+<Q?[/f/;0r"ag3H\'3K$l:H69aA[!RP\n'
                   ';!9]W0juYYOP8asF\\(3a=[l@[M$RDU=@PIrD-\n'
                   '\'"Bi7$URfTGBfAa\'mtg-"-\n'
                   'X`>d_;67E:?[G+"EpC,*BeaCpBjLteRGGPQBdoe;7bk@\\kA9V<\n'
                   'l\'AgW%\'Z&.2GL[<im+["XKmA+uQe\':=6)l@Vo0i]?Fj^IgOMUC\n'
                   ']',
               48: 'Gat=ih.tb!&AVr4d66-\n'
                   "h[*V'&5gYj8N7;uTkMp+oA*ZUN0j%fZ:kiH&ObmS;fP-X<@=-\n"
                   "V\\DL^mLK?8#t8@I,no,1+`8U!DV8_j'<^OE@Ladtlnlm'%f4u,\n"
                   '48e-emq)][*-G_1K(o[_E0lc@E^lQsu]?H_OM-MlL&G+1)ma:.\n'
                   'm<4c0i.@hL%.pAI!DVNV!+e;M]cNsYB/,X`J<e!h;KA?$uf%&[\n'
                   'e$q*(PJRNOf_KI@?+@_OE2H,5U26K,j+PB:h9P-dll8(S-\n'
                   ']Qo9MtNc>a8><Cm=qDa)!nGEOH!aFW0\\:R*I1?AM7.LT1h!S%s\n'
                   '[(*cs\\e^q!+*tlF>W`l8BT^,;9nM[_Zc=J59mmIoEZ=k!OIo6t\n'
                   'e+%N!$_uVQg$$8h5a=Yq49IitZ)dbl,(ESQ35e";F,Vj#dDD$6\n'
                   'PaiY;I=qd[:;<eO\\4,uo91M`nbN%j?Ds5Wi=)[lOX:;W5-\n'
                   '804dVfh#8YL)QApD[fA=+(Aj3bhCKt`fsOIOK8+Sd![((H,#tA\n'
                   "n/X&/R.:<Sh4%Qs[=o^)`).(%jW()?#co>4E\\**8#dN$_`'ho>\n"
                   ":3!FWc*kR'<B?hsSbE`GB;=lgBo?Y<K&uBgot,^YZ](`N'CF0M\n"
                   'nl_u)Uo`0?[ptKApSF"5*[FkU.cU.M!q@Uq[^<?r#7*^n3PiNr\n'
                   "&KI#@au<h$OEb_fC>Mr\\]#kq>1(G]'\\$#&M*j9T+!]TJd_mlX*\n"
                   'X5ij<$J=Ho(\\N%;MBcRX=hWhF-nT#`O9AK=+Ds.^..Znu=1KZh\n'
                   "8BW9.it0I\\9cO>q%*b_`e#]^L1YGhCE'-\n"
                   '*e@Ag5;^#M)`hD/obD4@]bFY2E)D55Rf:FrDR[YR<)?$jr;a*Q\n'
                   'KRS,0q+Y\\fP`J\\+\\O";5DI!Cj:24o',
               49: "Gatn$cYq8d'ZZ%Y)Mb%d&S!mVaV-aX#duWce$K?.6Em/c!\\lr-\n"
                   'dtF7@RA2Z[eHAtb89"<_a$7UOK9ND4dCI$qHY`$$YM])ZT:P`L\n'
                   '`fH`Bf93m0^Ni@6OYJW&^oMB%5u7#]B&b<E^=Hub2I!e>6T6*[\n'
                   'L=pA,4l&B,#/E0XQqn9O.%)84Lrbg6OVaN2Db+iW"2*XR8I0]T\n'
                   '&,Tmf-\n'
                   "h&.b^VL`Ef>T_>6='M1jW;e6s#$rq?U9k]MTZ@i5h3gPJYI@2$\n"
                   "C*+I\\8h^O]83TrX!LO[=2n_;(ujC^dG'QO;m6+o`Yo(;H<'1-\n"
                   "RK%:XnKdX'b?8;d9iiuoC,T;@]X2LX](#UfBMHpTl0^\\>#t*B-\n"
                   "B?2;s06sJCk20Y:%%qfU'O80ZM]B+4PbOVSX%VUgeOLfb%tPp5\n"
                   "C3`Ub1'6]hCgMZ;O#bOmQ?c'7\\T0*CBR2RJ\\QU!)kXM//-\n"
                   'aKgi/?$e=Qn01FcgpmfD2TqA`>fTZ:/5dYUY%,CY@fCq`I4D"L\n'
                   '7CMoNok,H[s:GRG=8U;(07c1fY"D!C5#U]!QkgU3LTKBrrpBI>\n'
                   '@"&\'dE?a;pnZ?Wr%,O\\&qX\\5\\_k)C&k9%RTg4"+E0gLq^*98af\n'
                   "/M,m7Ork'5^YJ\\4`aoTnOO5)#[B7ncbcaf<W)V@Y!CRPW*MRYS\n"
                   "pa!-+[ZqujEcAj72;?NLl)\\&cl%[,1_W']W-\n"
                   ';oCAoWBKpGRur*C^P1D(i\\e`ra1aFSt\\e_EoGS;]h(JQoUoQq0\n'
                   "5;*$&:8O&k($M'9-\n"
                   'Yg1\\I8+1(Gnqm!r3^6&#&;7Y>eVX4+I;\\u"-\n'
                   'c[YM$5kVRG2C:6jlCpjer[S=)B$FdIs`LUGhZ45:J)Fh@!\\.HL\n'
                   '%03!K;"9',
               50: 'Gau0A95i9E&B5no3S94R"0&"7Q?#Qj8tGa>-\n'
                   '5)CI6)dHf\'"r><V!G*^59ei6jF@C-\n'
                   "]eTEqINiRJ:=cRH>U97Coo3Ts^7FrbIc'toHhTgHFP*A_jG#Y8\n"
                   ':k?_)Pb?WQZ(0eR")Fpj;,9:=X*sRNWTHb;O8:p63!%UDTQZ.d\n'
                   'RC2FV\\>a%dfKi8Ao.:Yrdi>uq$`rLM70m`(Pg]qF^eZrb!T/Dj\n'
                   'jEC;,*I]d..8]hiJOs4".NE[-O@06R-\n'
                   '@Gr!:VE$Ni#/+RRJdo)1MIQDQa_3Y`(IO0#!%)i<_k%_5g%$GS\n'
                   'nOFDG)c0#0)3Q*-\n'
                   '"[^Mf>+1`:uX"dB9JU,LalI(gLSK21fLR(gFAA$G(K)#.+D_.k\n'
                   '6_?`<:p?(D[m\'KMb:9K8td;[\\hNA#jSMiXA<"$Z9hBVOV0+>(<\n'
                   'H<"\\9uL(QiELF68[`[p>Iu/!))en]&L\\?.Ec2]YBIuN&,)i`cm\n'
                   'b8F*FRu-\n'
                   '[:VhK\'H9:k4eZ6("9R8);X&Te7oe.5NeB)<:PnDZPi0UBjQMm(\n'
                   'qGKl0g)FB+?R9nR4iGkG:$EC7mq=UnQ[k[+ND"7E2#RRE,j-\n'
                   'Qf@NRh3Q6<l`W^9K59AeQgYo.5A(cGT>#;fcFaYP9JX(0^RdLu\n'
                   'KA*>^T,)*?jc/ao:r:0+fK23TLTq=!7p!jBg.\\ZMX\\S*5&Ylq%\n'
                   'I0\'\'=8$9\'J30!"k]:XjPV^qD1u9Rg<Oopf]X26el7\'rRau\'-\n'
                   'lLh#Q_m"6(L1^V6N#oeueKF]b2i"8MD!<`cco8=AboE)QU?N4T\n'
                   'pCC0As$m'}

# --- Public levels on showcase ---

SHOWCASE = ['GatU19lJKG&B,2[OIQR_g594(LeEW"e/rD[j?c[393!NCU,Q&u\n'
            'g0Vg#CHIDZ"\\Tu\'qqbGXr)VBD*IlR^8BHeNg"DeH\\*I23S&`;*\n'
            '-P,3DLV,U=HZ83%Y2=rS4@=\\];o5/2(_4qMeBeV$Z7X.EU:_i[\n'
            'd\\$ub?mNo?E<p2,-\n'
            '%F2lgBRsX+i&QbKB:?$n6ghM#Zs)MWXQs+^ilSVfYR!mDq_A]>\n'
            'M*l3Oj,5dlQD[rH%C+-\n'
            'H3+;>@0jR42KV.8DU=*Q_TW[=UIoSAqX%S`X<Ib!(60N\\r.:(9\n'
            'j2O!aEJtm=U+-%0GCS$_PWWE(H9jXZ:Uo$+iZf$&)mu-\n'
            'b+P`IWH+kJtg0Xhl4;+-&5cnZVBU*o>MJ0^JX-UXIL2^L57J0^\n'
            "?=igJDgd)[e3;SLFDFDtD&WO?VN]tk/qS'>n<q4=AZZ;q1Q&_?\n"
            'u/g@)RQ?ZQ=@fDme-\n'
            '1%5,aBiEEr"k!5Xjg*B`O@BKl&5EoaF_`^8HQb7hX1\'mfb&*qC\n'
            'KRZbqsK;E#5PTA(&[;P^\\dASn-\n'
            '*1m9<l&EP)^tH=T(FHhFRUKfZi(pghH=[G1cRs336GibZfNh$f\n'
            '<;JIAF7jm\\6f7f41,e<]1Ft?TT=D]8:+KC639I45MN9Djn+P1R\n'
            '1%A9i(F0r_dYQ:,IjXAg>`+OP5q@<>928Bq12gR!>8IrGnm/9Z\n'
            "F_9l=(q'om1D/5E48,,FafYI7V?_MQVeaZbJ^9KRk\\1P11Ql86\n"
            '=/h-Aq@j;R"TiOs3Gk/=AjGMg`Dq"9\\*;;]NrW63Gs=$ep:c.0',
            "Gaua<cYM8h'ZXjP;AdE,j^=^<`\\%R^e?Kr?c=M^XrLaN,2V;Gk\n"
            'Tf>r86fMLO5?o%AGMVuds3>e!96OUp^gQsb[Nt%LpN]P!r,_>Q\n'
            "fDT@XVorFr`/=eU@WZc^U?%c*L]H&A0S3'i-\n"
            'CNm""#k)kB]\'pl[c8APgRG_@ADj4Y;rB<(,CGuR(#JS6\\\'eIhI\n'
            '/b3nOX]/&Ds7.O+2FMHj"Q+\'qW6FH@/Bm:8K%Mu2m1s:1Uu!>X\n'
            's%1iAea7Y$tM$C/gSG"l/MH!g-\n'
            'sfc)+UQ!5,tWNU!:!kOBpa/aXOp395h,<BE+P;EQhUN,*oIq=s\n'
            '"GSSW]e3h&T)+?L@!o[NhAc`)mW+/A8)>9\'YPB8>7G_C@8\\&DN\n'
            'lsg&]h&Z[T0Md,)bh\\?j^ebT`t^b"BI/8aYd`r8g*_j"N?aege\n'
            '8j^]jCllp2L.$GZP3/oh`$=]qET$XCKrGg54T6].g1k/%h:O\\e\n'
            "=FuWbYJ>D;)a#T*LWHSc(T8[3E1;gKDj#:',3dh,)](;ccJCJ8\n"
            '7<hT+pHiH=D=*VGbnik2n6$%MI+6%p4aZ;mHb*jG_MuYU&Q%LG\n'
            ']O=nO6]sA6Q%82Zl6iO08h`Qg7`:I(<RVO<TWc(e%)d/Ct]k]B\n'
            'TsHBg4n.*aWa3QJjEaoDke_p@sL5@*`gUiWd,6%gO?E;DRqJl4\n'
            '8MukKs9nn^&ZDnL3nh^>jQm`N_poD4b8m$s_P>/bK&E0e).g',
            'Gaua<gPaNG\'Sd^qd[*3)ZL1A0$0]9QU"_D<RhS8akTWn9\']0[o\n'
            ',h#Jq8P518(L1)"kKW&elf:)_8a>EZSu.pGb:hbCR3oBJ58X8[\n'
            'q<+"9([IX$+UM!,I6dE.hHmg=LOgM+bVR.!)ir"fVtt\'f2pJnl\n'
            "k\\leQ:DQ$D;r[+EaZ@#_;c`&B,'k0JRj$-\n"
            "bLpp'^IuZn%`*<!;O1rL@d(@L4(N@O2'Kpt3q0tkSL3GnFcAiE\n"
            "oKqba^BS,d@lFQ4]V#3GY[Nj!OP!BIUMS<XB;$F#(.,'1c@@hc\n"
            ',.5]OZYD=0aB2.kQ9p&Q$XGS74-\n'
            'W):g5.;;uPZ\\S4F4D[b<cH2LMKH!GSIALu_0\\`#B?2UA=IVZ,F\n'
            'a6aDBlI#CYj-)IZ%o%lAb0CG*sE"/*^anj7`D&-\n'
            "**UULN<ZeJ<qGZ\\\\IJtlIU#]'4l2#]=l!Br;8(2IkW/Ps6aPB:\n"
            "H/Br9f<.s9/8bQH5ktchV7pk2'6`^eW-\n"
            "3E07p>4Dd4=uD6eC2VF5d*aDWU;4!n)M9NjmV?'1N$hMh02@St\n"
            '.>Znpbq3eLG.4UIS=;s/I(BZ=<FYd#McKc0"W%]dg\\#oFd=sDb\n'
            'bm*4^+"&hHdm$Xk)?t7-X#N\'ebcoUjg_`_X-Ohkl(*TpZ!ohN[\n'
            '$c8;+:>ZX)L-\n'
            "'b`iV$$e+fC]HW$eM/,)*7iZ#T@`QM&1A3873jgP`AiZ/cRFn.\n"
            'a.r;_MiQQ+=2"NlbL(oBW!\';:YT`',
            "Gb!#YcYM8h'Wu.B%Pu0LP[8ZTfFAcNXW9'O',VEU42qO?g)YN:\n"
            '/?(6Q:5G,53"37-\n'
            'DL;>3kMLQ.PTEGjc&7\\Uo\\QM7I7Wq$SYo9VXlS*"+0L!/T$f\\a\n'
            '%mlA(3h&9ml(!@\\Z^bO[3UU"?hP"ZVL5n\'s#Niu2AF&F&U]E:)\n'
            'oKG5k(]Jfn]^_bgRu:hhn6]T3A8OYG&SCt\\Sa[5^_*@_m(Oh"l\n'
            'Nr3i*mH?42O5T>BB0>2CQM[QgV"T=<OIE^_\'1:_\'Yt=<g<\\ma/\n'
            "!X\\Z8-&fd7)p';pgpk[3ZE_mh+C:>e#o%Z2\\hXC&X3+397Q-\n"
            ':uRQ1nX?09gS::&lUQT1:jTOsGZF,[-\n'
            "&3_t!2>3$T$,KUjQ),Wmb&gc;W'kHV:K19<)6K8rAQ#302K%f@\n"
            '7Q&jiXd_P?r;2nTKdW:YmW2j.SJ1,A-\n'
            "2)AZ+d.u'^pr*R;$3^ZtTp0cV7l?A06h`=%IC'AK;S3MC28/4s\n"
            'pLJEeo"&;b7CUZH_d)(F\\lIq_$?$Vjq]^@lY9XY!5DW[1HQt_B\n'
            "c6(Ac\\Fj`bYkT8qkpX1NMiUMJ'$m^(MVjOD<eoG(c^;mlNs\\P4\n"
            '%VL_.DEAn^]<:IAH`[+`n[LI?]7Z\\,7+YqCcX"BaA\'kmmJ></6\n'
            '"jVA']

# --- All public levels ---

PUBLIC = ['Gb!$D5tf*\\&;:Qo4]nBl<9S&89,5i2M+u76MR4iO&G.:j2OduN\n'
          '0hH(W0aC#5F*%8o-\n'
          "E0Vb6rOdV0.`T`m*(f)aa9D#^71TaY<'mOH\\3Fd-iB:f+I(1m:\n"
          'A/BdZKQf_/Bd<Z6etXNV7AnQVP1"Z@u$SC#hg=36]\\aa^HrG/4\n'
          'suIW,i$$*,@[a:$^9;7=HPnho3EQ)iXGq*g];Q.8c/:9CQE_$0\n'
          'HI@W-\n'
          '._)qUfDNZIjZ9nr+5j,63%WaVih=]ZdGk!L<9aL?E(U!^-\n'
          'ee:/&)bNR>NbYcZ0l:b*YIkS0V_P8F)Yp%0N.IOH.ep*KPnFZF\n'
          'X:8opU$tF1ppXA:+PO-\n'
          'TD],m@/@WRu>r?l&N*Je--\\p<Lr2]k32OG-IpEJIRF-hJ-XXk]\n'
          '0:6jVZb0iGPshW&Yd<lg^B0*iL@Y`nEr%X2gJ$pD$u1RM:D>6k\n'
          'CM;]@U1Ji[3L`cEJt?Zd!(Zr#ri<>^:/r=\\RPs"<3\\<oTa?\\d]\n'
          "?+kh:gI^MRjj5lZs#f&jd']hh52*SD-\n"
          '9plI@JA?V&H238Q?KmgjB,.m-=-',
          'GatU19lJKG&B,2[OIQR_g594(LeEW"e/rD[j?c[393!NCU,Q&u\n'
          'g0Vg#CHIDZ"\\Tu\'qqbGXr)VBD*IlR^8BHeNg"DeH\\*I23S&`;*\n'
          '-P,3DLV,U=HZ83%Y2=rS4@=\\];o5/2(_4qMeBeV$Z7X.EU:_i[\n'
          'd\\$ub?mNo?E<p2,-\n'
          '%F2lgBRsX+i&QbKB:?$n6ghM#Zs)MWXQs+^ilSVfYR!mDq_A]>\n'
          'M*l3Oj,5dlQD[rH%C+-\n'
          'H3+;>@0jR42KV.8DU=*Q_TW[=UIoSAqX%S`X<Ib!(60N\\r.:(9\n'
          'j2O!aEJtm=U+-%0GCS$_PWWE(H9jXZ:Uo$+iZf$&)mu-\n'
          'b+P`IWH+kJtg0Xhl4;+-&5cnZVBU*o>MJ0^JX-UXIL2^L57J0^\n'
          "?=igJDgd)[e3;SLFDFDtD&WO?VN]tk/qS'>n<q4=AZZ;q1Q&_?\n"
          'u/g@)RQ?ZQ=@fDme-\n'
          '1%5,aBiEEr"k!5Xjg*B`O@BKl&5EoaF_`^8HQb7hX1\'mfb&*qC\n'
          'KRZbqsK;E#5PTA(&[;P^\\dASn-\n'
          '*1m9<l&EP)^tH=T(FHhFRUKfZi(pghH=[G1cRs336GibZfNh$f\n'
          '<;JIAF7jm\\6f7f41,e<]1Ft?TT=D]8:+KC639I45MN9Djn+P1R\n'
          '1%A9i(F0r_dYQ:,IjXAg>`+OP5q@<>928Bq12gR!>8IrGnm/9Z\n'
          "F_9l=(q'om1D/5E48,,FafYI7V?_MQVeaZbJ^9KRk\\1P11Ql86\n"
          '=/h-Aq@j;R"TiOs3Gk/=AjGMg`Dq"9\\*;;]NrW63Gs=$ep:c.0',
          'Gaua<bA5it&;RU1,o:!;&@g(,2Y</u[*cdW/0BbC,bYa86?3NH\n'
          '/Zg3_A/e0URR<d^c`P[r[u+_>nS1"+6;\'0Kd`g#9k1b[D+&@@#\n'
          'hq9K^I<]oTcdIc$jBq^/]oKFTIcAuO.#>4O$pct53.8uI2^:4j\n'
          '#]7IC2!mZRYabf13.9QLRi_Mj6oZT+/dn)#"e8nqnb@]JH2hk:\n'
          '=>oY8Fq::/Y\\B!!F2APRA5iD[07Mo)K^Cm^kI@/A5b;J]rBK=&\n'
          "_nXV(ndVAVgpH@I\\Iqgqe?e6t._fGc(ps^_NO<Mu'i2r5q`mnr\n"
          "*nOru5V/F@2/>5c+%X/j?Y6?!o'BjkOAp3K8#7K-\n"
          '!:j\\UC;%c\\;ZM*"G@FI1W$P8rfh\\FYD4tQGkc#K@V?CAiV5Yr%\n'
          "X&BrlO>dI+'h5ec[Z3[4-\n"
          'gUNFU/b9n4_,V"24(ms!cblan5a2YM630J]jq:%OT-2-\n'
          '/N(F/qdT__k)/mmJpUO1!s2c-\n'
          'o61Ib3]\\.#atkVa5^US9amA.<$tDNaj6YS]S.*l)ZoVh<afTcI\n'
          'l0-#C%!nVj\\fL54%-\n'
          'Df#kBNR]l7poZKd$&hcj7M(@(,NmY3"Enl\'bYN)d%!n!oJ*:mU\n'
          ':jRrrCMlh*V',
          "Gaua<cYM8h'ZXjP;AdE,j^=^<`\\%R^e?Kr?c=M^XrLaN,2V;Gk\n"
          'Tf>r86fMLO5?o%AGMVuds3>e!96OUp^gQsb[Nt%LpN]P!r,_>Q\n'
          "fDT@XVorFr`/=eU@WZc^U?%c*L]H&A0S3'i-\n"
          'CNm""#k)kB]\'pl[c8APgRG_@ADj4Y;rB<(,CGuR(#JS6\\\'eIhI\n'
          '/b3nOX]/&Ds7.O+2FMHj"Q+\'qW6FH@/Bm:8K%Mu2m1s:1Uu!>X\n'
          's%1iAea7Y$tM$C/gSG"l/MH!g-\n'
          'sfc)+UQ!5,tWNU!:!kOBpa/aXOp395h,<BE+P;EQhUN,*oIq=s\n'
          '"GSSW]e3h&T)+?L@!o[NhAc`)mW+/A8)>9\'YPB8>7G_C@8\\&DN\n'
          'lsg&]h&Z[T0Md,)bh\\?j^ebT`t^b"BI/8aYd`r8g*_j"N?aege\n'
          '8j^]jCllp2L.$GZP3/oh`$=]qET$XCKrGg54T6].g1k/%h:O\\e\n'
          "=FuWbYJ>D;)a#T*LWHSc(T8[3E1;gKDj#:',3dh,)](;ccJCJ8\n"
          '7<hT+pHiH=D=*VGbnik2n6$%MI+6%p4aZ;mHb*jG_MuYU&Q%LG\n'
          ']O=nO6]sA6Q%82Zl6iO08h`Qg7`:I(<RVO<TWc(e%)d/Ct]k]B\n'
          'TsHBg4n.*aWa3QJjEaoDke_p@sL5@*`gUiWd,6%gO?E;DRqJl4\n'
          '8MukKs9nn^&ZDnL3nh^>jQm`N_poD4b8m$s_P>/bK&E0e).g',
          'Gaua<gPaNG\'Sd^qd[*3)ZL1A0$0]9QU"_D<RhS8akTWn9\']0[o\n'
          ',h#Jq8P518(L1)"kKW&elf:)_8a>EZSu.pGb:hbCR3oBJ58X8[\n'
          'q<+"9([IX$+UM!,I6dE.hHmg=LOgM+bVR.!)ir"fVtt\'f2pJnl\n'
          "k\\leQ:DQ$D;r[+EaZ@#_;c`&B,'k0JRj$-\n"
          "bLpp'^IuZn%`*<!;O1rL@d(@L4(N@O2'Kpt3q0tkSL3GnFcAiE\n"
          "oKqba^BS,d@lFQ4]V#3GY[Nj!OP!BIUMS<XB;$F#(.,'1c@@hc\n"
          ',.5]OZYD=0aB2.kQ9p&Q$XGS74-\n'
          'W):g5.;;uPZ\\S4F4D[b<cH2LMKH!GSIALu_0\\`#B?2UA=IVZ,F\n'
          'a6aDBlI#CYj-)IZ%o%lAb0CG*sE"/*^anj7`D&-\n'
          "**UULN<ZeJ<qGZ\\\\IJtlIU#]'4l2#]=l!Br;8(2IkW/Ps6aPB:\n"
          "H/Br9f<.s9/8bQH5ktchV7pk2'6`^eW-\n"
          "3E07p>4Dd4=uD6eC2VF5d*aDWU;4!n)M9NjmV?'1N$hMh02@St\n"
          '.>Znpbq3eLG.4UIS=;s/I(BZ=<FYd#McKc0"W%]dg\\#oFd=sDb\n'
          'bm*4^+"&hHdm$Xk)?t7-X#N\'ebcoUjg_`_X-Ohkl(*TpZ!ohN[\n'
          '$c8;+:>ZX)L-\n'
          "'b`iV$$e+fC]HW$eM/,)*7iZ#T@`QM&1A3873jgP`AiZ/cRFn.\n"
          'a.r;_MiQQ+=2"NlbL(oBW!\';:YT`',
          "Gb!#YcYM8h'Wu.B%Pu0LP[8ZTfFAcNXW9'O',VEU42qO?g)YN:\n"
          '/?(6Q:5G,53"37-\n'
          'DL;>3kMLQ.PTEGjc&7\\Uo\\QM7I7Wq$SYo9VXlS*"+0L!/T$f\\a\n'
          '%mlA(3h&9ml(!@\\Z^bO[3UU"?hP"ZVL5n\'s#Niu2AF&F&U]E:)\n'
          'oKG5k(]Jfn]^_bgRu:hhn6]T3A8OYG&SCt\\Sa[5^_*@_m(Oh"l\n'
          'Nr3i*mH?42O5T>BB0>2CQM[QgV"T=<OIE^_\'1:_\'Yt=<g<\\ma/\n'
          "!X\\Z8-&fd7)p';pgpk[3ZE_mh+C:>e#o%Z2\\hXC&X3+397Q-\n"
          ':uRQ1nX?09gS::&lUQT1:jTOsGZF,[-\n'
          "&3_t!2>3$T$,KUjQ),Wmb&gc;W'kHV:K19<)6K8rAQ#302K%f@\n"
          '7Q&jiXd_P?r;2nTKdW:YmW2j.SJ1,A-\n'
          "2)AZ+d.u'^pr*R;$3^ZtTp0cV7l?A06h`=%IC'AK;S3MC28/4s\n"
          'pLJEeo"&;b7CUZH_d)(F\\lIq_$?$Vjq]^@lY9XY!5DW[1HQt_B\n'
          "c6(Ac\\Fj`bYkT8qkpX1NMiUMJ'$m^(MVjOD<eoG(c^;mlNs\\P4\n"
          '%VL_.DEAn^]<:IAH`[+`n[LI?]7Z\\,7+YqCcX"BaA\'kmmJ></6\n'
          '"jVA',
          'GauI4bA5it&;RUA,u=`]?uR`PKjL:4LE7sK1-\n'
          'Gb,>=("H;WoQo[54fkIYb)R,_n^5T3J2mDe0*qHJ)7,XaZFF[B\n'
          'h[\\m7<ll07Si7Sb2.)/(:eXj7YXn+OiT/^e\\P60TnAXY\\Vn3B)\n'
          'gL=/GFZ6k!8\\De);*1_Lp1.N&aQHn2mWE)-\n'
          '=:EZqt_diru\'u)=TVU-pE?\'0KgUrc"*UUG<[FGToA2tp4(M7_A\n'
          'C<V>u<78OhIGbCF3T*`\\Eqd#t=G6AGj1s+M2"3C8Y-\n'
          "1H?rrCYH=,DAdnN6a=\\n^[0p.0PsmT5qE%KR;ru&'B%r_*Wm$s\n"
          ']R\\HO"RX)=0:9N$/[i1t%ip&XPNFs1rEIBiJX"[L&,C;r%%Op0\n'
          '`0PcrDgF9FEDlKUOQ/bZ)0d-\n'
          '?Y9dg?18`RS8;/PMfWc$7G]lK^a%!fO(8?d5TInd034`n-\n'
          'NXaBSCJl3n*-\n'
          'WKR1LL&9Ed^QL]49eWWo1mrTmLWugRtp`(0H!Yo*hU]0`DCt_f\n'
          'e93[><Z=iZ@3$S!XDEF[=pO@0SF@+[KV5("&!s[[0n=kJ`hgh4\n'
          'LaeS@q#5*[)V%Y_NL3>&qXRRq@*LDdj4']

# --- Ranges ---

"""These are range objects that define different parts of the 
GLOBAL_STRS dictionary.

- GLOBAL_RANGE:          | The entirety of GLOBAL_STRS
- MAIN_RANGE:            | start to TOWER (20)
- PACK_RANGE:            | TOWER + 1 (21) to end

PACKS is a dictionary mapping ranges to level packs.

-> Hidden Blocks:        | TOWER + 1 (21) to 25
-> Countdown Blocks:     | 26 to 30
-> Gravity Blocks:       | 31 to 35
-> Teleporters:          | 36 to 40
-> Launchers:            | 41 to 45
-> More Locks:           | 46 to end
"""

GLOBAL_RANGE = range(min(GLOBAL_STRS), max(GLOBAL_STRS) + 1)
MAIN_RANGE = range(min(GLOBAL_STRS), Constants.TOWER + 1)

PACK_RANGE = range(Constants.TOWER + 1, max(GLOBAL_STRS) + 1)

PACKS = {
    range(PACK_RANGE.start, 26): "Hidden Blocks",
    range(26, 31): "Countdown Blocks",
    range(31, 36): "Gravity Blocks",
    range(36, 41): "Teleporters",
    range(41, 46): "Launchers",
    range(46, PACK_RANGE.stop): "More Locks"
}

# --- Data Structures ---

class Coordinates(ABC):

    """Coordinates is an abstract base class which C
    and FrozenC inherit from. It implements all the
    mechanisms for a coordinate system, as well as
    special iterators like Coordinates.line and
    Coordinates.circle which are used in the editor."""

    @property
    @abstractmethod
    def x(self) -> int:
        ...

    @property
    @abstractmethod
    def y(self) -> int:
        ...

    @property
    def norm(self):
        return abs(complex(self))

    def __add__(self, other: Coordinates) -> Self:

        """Add two coordinates as if they are vectors."""

        if not isinstance(other, Coordinates):
            return NotImplemented

        return type(self)(x=(self.x + other.x), y=(self.y + other.y))

    def __sub__(self, other: Coordinates) -> Self:

        """Subtract two coordinates as if they are vectors."""

        if not isinstance(other, Coordinates):
            return NotImplemented

        return type(self)(x=(self.x - other.x), y=(self.y - other.y))

    def __mod__(self, mod: Coordinates) -> Self:

        """<a, b> mod <c, d> is equal to <a mod c, b mod d>."""

        if not isinstance(mod, Coordinates):
            return NotImplemented

        return type(self)(x=(self.x % mod.x), y=(self.y % mod.y))

    def __abs__(self) -> Self:

        """Return the absolute value of a coordinate. NOTE:
        this is a component-wise operation. |<a, b>| is not
        the length of <a, b> or sqrt(a^2 + b^2), rather it is
        a new coordinate <|a|, |b|>. For the length of <a, b>,
        use the Coordinates.norm property."""

        return type(self)(x=abs(self.x), y=abs(self.y))

    def __mul__(self, i: int | float | Coordinates) -> Self:

        """Scalar multiplication of a coordinate by a number.
        This operation acts just like with vectors."""

        if isinstance(i, Coordinates):
            return type(self)(x=(self.x * i.x), y=(self.y * i.y))
        else:
            return type(self)(x=(self.x * i), y=(self.y * i))

    def __rmul__(self, i: int | float) -> Self:

        """See __mul__."""

        if isinstance(i, Coordinates):
            return type(self)(x=(self.x * i.x), y=(self.y * i.y))
        else:
            return type(self)(x=(self.x * i), y=(self.y * i))

    def copy(self) -> Self:

        """Return a new, deep-copied coordinate. Works
        by creating a new instance with the same x and y
        coordinates."""

        return type(self)(self.x, self.y)

    def __iter__(self) -> Iterator[int]:

        """Iterator for coordinates; first gives the x-coordinate,
        then the y-coordinate."""

        yield self.x
        yield self.y

    def __complex__(self) -> complex:

        """Creates a complex number out of a coordinate."""

        return complex(self.x, self.y)

    def adj(self, direction: str, g: Literal[1, -1]=1) -> Self:

        """Returns the adjacent coordinate in the given direction.
        An optional argument g is given to indicate gravity, or
        whether to flip the north and south directions."""

        c = type(self)

        x, y = self

        match direction:

            case "w":
                return c(x, y+g)
            case "a":
                return c(x-1, y)
            case "s":
                return c(x, y-g)
            case "d":
                return c(x+1, y)
            case "as" | "sa":
                return c(x-1, y-g)
            case "sd" | "ds":
                return c(x+1, y-g)
            case "wd" | "dw":
                return c(x+1, y+g)
            case "aw" | "wa":
                return c(x-1, y+g)
            case "ww":
                return c(x, y+2*g)
            case "ss":
                return c(x, y-2*g)

    def adjs(self, *directions: str, g: Literal[1, -1]=1) -> set[Self]:

        """Takes in a string of directions and returns a set of coordinates
        adjacent to self in those directions. Optional parameter g is included;
        see Coordinates.adj for more info."""

        return {self.adj(d, g).as_frozen() for d in directions}

    @classmethod
    def arc(cls,
            endpoint_1: Coordinates,
            endpoint_2: Coordinates,
            invert: bool=False
            ) -> Iterator[Self]:

        """Draws a rectangular arc between two endpoints. Prioritizes the
        y-direction over the x-direction. The invert argument switches the
        order of the coordinates."""

        if not (isinstance(endpoint_1, Coordinates)
                and isinstance(endpoint_2, Coordinates)):
            raise TypeError(
                "expected endpoint_1, endpoint_2 to be of type Coordinates"
            )

        if invert:
            endpoint_1, endpoint_2 = endpoint_2, endpoint_1

        x1, x2 = endpoint_1.x, endpoint_2.x
        y1, y2 = endpoint_1.y, endpoint_2.y

        # Go in the vertical direction
        a = 1 if y1 <= y2 else -1
        for y in range(y1, y2 + a, a):
            yield cls(x1, y)

        # Go in the horizontal direction
        a = 1 if x1 <= x2 else -1
        for x in range(x1, x2 + a, a):
            yield cls(x, y2)

    @classmethod
    def box(cls,
            endpoint_1: Coordinates,
            endpoint_2: Coordinates
            ) -> Iterator[Self]:

        """Draws a rectangular box from two opposite endpoints
        by drawing two arcs."""

        for invert in (True, False):
            yield from cls.arc(endpoint_1, endpoint_2, invert=invert)

    # The next two/three methods are HEAVILY documented.
    # Just the nature of Bresenham's algorithms.

    @classmethod
    def line(cls,
             endpoint_1: Coordinates,
             endpoint_2: Coordinates
             ) -> Iterator[Self]:

        """Yields coordinates for a line between two endpoints;
        uses Bresenham's line algorithm."""

        x0, y0 = endpoint_1
        x1, y1 = endpoint_2

        # Displacement
        dx, dy = endpoint_2 - endpoint_1

        # Decompose displacements into sign and distance
        sx, dx = 1 if dx > 0 else -1, abs(dx)
        sy, dy = 1 if dy > 0 else -1, abs(dy)

        # Prioritize horizontal over vertical.
        M, m = cls(sx, 0), cls(0, sy)
        major, minor = dx, dy

        # Prioritize vertical over horizontal for steep lines.
        if dy > dx:
            M, m = m, M
            major, minor = minor, major

        # Error term. Decides when to go in the minor direction.
        D = 2*minor - major

        current = endpoint_1.as_normal()

        for _ in range(major + 1):

            yield current

            # When the error gets too large, go in the minor direction.
            # Then push the error down.
            if D >= 0:
                current += m
                D -= 2*major

            # Build up the error for going in the major direction.
            current += M
            D += 2*minor

    @classmethod
    def _octants(cls, center: int, x: int, y: int) -> Iterator[Self]:

        """A subroutine that yields coordinates for octants of a circle
        according to Bresenham's algorithm."""

        c1, c2 = cls(x, y), cls(y, x)

        # c2 completes the arc from the other side
        # of the quadrant. It is reflected over y = x.

        # Rotate directions of c1 and c2.
        for mul in cls(1, 1), cls(1, -1), cls(-1, 1), cls(-1, -1):

            # add directed <x, y> to center
            # to readjust to radius.
            yield center + mul*c1
            yield center + mul*c2

    @classmethod
    def circle(cls,
               center: Coordinates,
               radius: int
               ) -> Iterator[Self]:

        """Yields coordinates for a circle with a given center and radius;
        uses Bresenham's circle algorithm."""

        x0, y0 = center

        # Error variable: tracks how far outside <x, y> is.
        f = 1 - radius

        # Slope of the circle (derivative). How much to change the error
        # given a movement in x or y; how much x or y is pushed outside.
        fx, fy = 1, 2 * radius

        # Coordinates
        x, y = 0, radius

        # Root coordinates
        for offset in [
            cls(0, radius),
            cls(0, -radius),
            cls(radius, 0),
            cls(-radius, 0)
        ]:
            yield center + offset

        # Note that <x, y> sweeps out an arc from 90 degrees to 45 degrees.
        # x is smaller than y until x = y = about sqrt(2)/2.
        # Then, the octants are drawn.
        while x < y:

            # ERROR IS TOO LARGE.
            if f >= 0:

                y -= 1 # Pull y closer to circle.
                fy -= 2 # Decrease the correction factor.
                f -= fy # Subtract error.

            x += 1 # Move x forward, pulls x farther from circle.
            fx += 2 # Increase correction factor.
            f += fx # Increase error.

            # x and y are reflected to complete all 7 other arcs as well
            # as the normal 90-45 arc.
            yield from cls._octants(center, x, y)

    def __str__(self) -> str:

        """Clean vector-like representation for coordinates."""

        return f"<{self.x} {self.y}>"

@dataclass(slots=True)
class C(Coordinates):

    """A concrete dataclass implementation of the Coordinate ABC.
    Is mutable, meaning the x-value and y-value can be changed.
    Includes new dunder methods:

    - __iadd__ or +=
    - __isub__ or -=
    - __imod__ or %=

    Supports as_frozen, which is a conversion to FrozenC.
    Supports as_normal, which exists for duck-type compatibility
    with FrozenC, to convert to normal coordinates regardless
    of type.

    The default value for coordinates is <5, 3>."""

    x: int = 5
    y: int = 3

    def __post_init__(self) -> None:

        """Checks that both the x-value and y-value are integers."""

        if not (isinstance(self.x, int) and isinstance(self.y, int)):
            raise TypeError("coordinates are not integers")

    def __iadd__(self, other: Coordinates) -> Self:

        if not isinstance(other, Coordinates):
            return NotImplemented

        self.x, self.y = (self.x + other.x), (self.y + other.y)
        return self

    def __isub__(self, other: Coordinates) -> Self:

        if not isinstance(other, Coordinates):
            return NotImplemented

        self.x, self.y = (self.x - other.x), (self.y - other.y)
        return self

    def __imod__(self, mod: Coordinates) -> Self:

        if not isinstance(mod, Coordinates):
            return NotImplemented

        self.x, self.y = (self.x % mod.x), (self.y % mod.y)
        return self

    def as_frozen(self) -> FrozenC:
        return FrozenC(self.x, self.y)

    def as_normal(self) -> C:
        return self

@dataclass(slots=True, frozen=True)
class FrozenC(Coordinates):

    """A concrete dataclass implementation of the Coordinate ABC.
    Is immutable, meaning the abscissa and ordinate cannot be changed.

    Supports as_frozen, which exists for duck-type compatibility
    with C, to convert to frozen coordinates regardless
    of type.
    Supports as_normal, which is a conversion to C.

    The default value for coordinates is <5, 3>."""

    x: int = 5
    y: int = 3

    def __post_init__(self) -> None:
        if not (isinstance(self.x, int) and isinstance(self.y, int)):
            raise TypeError("coordinates are not integers")

    def as_frozen(self) -> FrozenC:
        return self

    def as_normal(self) -> C:
        return C(self.x, self.y)

class Map(ABC):

    """An abstract base class for a rectangular game map. Supports
    a Cartesian coordinate system, where unlike a traditional 2D
    list in Python, the origin exists on the bottom left corner
    instead of the top left corner."""

    DEFAULT = [
                  ["#" for x in range(Constants.X_LEN)]
                  for y in range(3)
              ] + [
                  [" " for x in range(Constants.X_LEN)]
                  for y in range(Constants.Y_LEN - 3)
              ]

    def __init__(self, _map: list[list[str]] | Map | None=None) -> None:

        """Initializes a Map object from a 2D list or another
        Map. If no such map is provided, a default map
        is initialized. (This is used in EditorMode.)

        Note that due to the coordinate system, maps are actually
        stored in reverse. This creates a Cartesian coordinate
        system where the y-coordinate is flipped. The direct
        constructor expects a flipped map. If building
        a map manually through lists, make sure you use
        the Map.from_visual constructor which automatically
        flips your map before sending it into __init__."""

        if _map is None:
            _map = Map.DEFAULT

        if isinstance(_map, Map):

            # Deep copy the map's internal list
            self.map = [row.copy() for row in _map.map]

        elif isinstance(_map, list):

            if not Map._valid_list(_map):
                raise ValueError("not a valid list")

            # Deep copy the map
            self.map = [row.copy() for row in _map]

        else:
            raise TypeError(f"{_map} is not of type list or Map")

    @classmethod
    def from_visual(cls, game_map: list) -> Self:

        """An alternate Map constructor that takes
        in a 2D list in non-reversed order and flips
        the map to adjust for the coordinate system."""

        return cls(list(reversed(game_map)))

    @staticmethod
    def _valid_list(_map: list):

        """Verifies whether a 2D list can be turned into
        a Map object."""

        if not _map:
            return False

        # All rows are lists
        if not all(isinstance(line, list) for line in _map):
            return False

        # All rows have only characters in them
        if not all(
                isinstance(char, str) and len(char) == 1
                for line in _map for char in line
        ):
            return False

        # All lines of the map must have uniform width
        if len({len(line) for line in _map}) > 1:
            return False

        return True

    """Properties for the length and width of a map."""

    @property
    def x_len(self) -> int:
        return len(self.map[0])
    @property
    def y_len(self) -> int:
        return len(self.map)

    @classmethod
    def solid(cls,
              char: str,
              length: int=Constants.X_LEN,
              width: int=Constants.Y_LEN
              ) -> Self:

        """Returns a map filled with one solid character, with specified
        length and width."""

        if len(char) != 1:
            raise ValueError(
                f"expected string of length 1, got {char!r} of length {len(char)}"
            )

        return cls([[char for x in range(length)] for y in range(width)])

    def __iter__(self) -> Iterator[list[str]]:

        """Note: iteration on a map will return the lines in *reverse*
        order. To get the visual order of a map, use the reversed()
        function.

        This convention is useful when enumerating rows, such as:

        for y, line in game_map:
            ...

        """

        return iter(self.map)

    def __reversed__(self) -> Iterator[list[str]]:

        """Note: reversed iteration on a map will return the lines in
        *visual* order. To get the true reversed order of the map,
        iterate directly or use iter()."""

        return iter(reversed(self.map))

    def __eq__(self, other: Map) -> bool:

        return type(self) == type(other) and self.map == other.map

    def __contains__(self, char) -> bool:
        return any(char in row for row in self.map)

    def __len__(self) -> int:
        return self.y_len

    def copy(self) -> Self:
        return type(self)(self.map)

    def __format__(self, format_spec: str) -> str:

        """Returns a formatted version of a map according to a format
        specifier. The format specifier should be two characters long:

        - h: the horizontal border character ('~' on default)
        - v: the vertical border character ('|' on default)"""

        n = len(format_spec)

        if n > 2:
            raise ValueError(
                "expected format specifier with length 2 or less, received "
                f"{format_spec} of length {len(format_spec)}"
            )

        h = format_spec[0] if n > 0 else "~"
        v = format_spec[1] if n > 1 else "|"

        lst = []

        horizontal_border = f"{h*(self.x_len+2)}"

        lst.append(horizontal_border)

        for row in reversed(self):
            lst.append(f"{v}{''.join(row)}{v}")

        lst.append(horizontal_border)

        return "\n".join(lst) + "\n"

    def __str__(self) -> str:

        """Returns a string representation for a game map. Uses the format
        function with default values h='~', v='|'"""

        return format(self, "")

    def _bounded(self, key: Coordinates) -> bool:

        """Returns whether the key is bounded within a map. In other words,
        it returns whether the key can be used as an index on the map.

        One of the main uses of this function is to bound the player's
        coordinates inside the map."""

        x_in_bounds = 0 <= key.x < self.x_len
        y_in_bounds = 0 <= key.y < self.y_len

        return (x_in_bounds and y_in_bounds)

    def __getitem__(self, key: Coordinates | int | slice) -> str | list | Self:

        """Returns the result of the map being accessed with a key.
        The data returned varies by type.
        - Coordinates: will return the character at that coordinate,
        returns NaC if out of bounds.
        - int: returns the row of all characters at that y-level as
        a list.
        - slice: slices the map, returns a new Map object."""

        if isinstance(key, Coordinates):

            if not self._bounded(key):
                return Constants.NaC

            x, y = key
            char = self.map[y][x]
            return char

        elif isinstance(key, int):

            return self.map[key]

        elif isinstance(key, slice):

            return type(self)(self.map[key])

        else:
            raise TypeError(
                f"{key!r} is not of type Coordinates, int, or slice"
            )

    def enumerate(self) -> Iterator[tuple[C, str]]:

        """Returns an iterator that yields coordinates as well
        as the character at that coordinate."""

        for coord_tuple in product(range(self.x_len), range(self.y_len)):
            coord = C(*coord_tuple)

            yield coord, self[coord]

    def find(self,
             chars: Iterable[str],
             *,
             include_character: bool=True
             ) -> set[tuple[FrozenC, str] | FrozenC]:

        """If the argument chars contains a single character,
        then self.find returns a set of all coordinates where
        that character is found.
        If the arguement chars contains multiple characters,
        then the behavior varies with the argument include_character.
        - include_character=False: similar behavior to in the single
        character case, returns coordinates where any of the characters
        are found.
        - include_character=True: returns a set of tuples each containing
        the coordinate and the character found at that coordinate."""

        result = set()
        for (x, y), char in self.enumerate():

            if char in chars:

                result.add((FrozenC(x, y), char)
                           if len(chars) > 1 and include_character
                           else FrozenC(x, y))

        return result

    def reflected(self, dim: str="x") -> Self:

        """Reflects the map over the x or y-axis. The axis
        is determined by the dim argument."""

        if not isinstance(dim, str):
            raise TypeError(f"expected str object, got {dim!r}")

        if dim == "x":
            return type(self)(self.map[::-1])
        elif dim == "y":
            return type(self)([line[::-1] for line in self.map])
        else:
            raise ValueError(f"expected 'x' or 'y', got {dim!r}")

    def replaced(self, old_char: str, new_char: str) -> Self:

        """Returns a new map which is identical to the current map,
        but where old_char is replaced with new_char."""

        if len(old_char) != 1:
            raise ValueError(
                f"expected string of length 1, got {old_char!r} of length {len(new_char)}"
            )
        if len(new_char) != 1:
            raise ValueError(
                f"expected string of length 1, got {new_char!r} of length {len(new_char)}"
            )

        lst = self.map.copy()

        lst = [
            [new_char if c == old_char else c for c in row]
            for row in lst
        ]

        return type(self)(lst)

    def count(self, char: str):

        """Returns the number of times char is found within the map."""

        return sum(row.count(char) for row in self.map)

class GameMap(Map):

    """A concrete, mutable implementation of the Map ABC.
    The __setitem__ method has been added, which allows a value
    to be assigned to a certain index in the map. Additionally,
    the replace method has been added, which replaces all instances
    of one character with another character. This is similar to
    the replaced method in Map, except that it is in place
    and directly edits the object's data instead of returning
    a new object."""

    def __setitem__(self, key: Coordinates, val: str) -> None:

        if not isinstance(val, str):
            raise TypeError(
                f"expected str object, got {val!r} of type {type(val).__name__}"
            )
        elif len(val) != 1:
            raise ValueError(
                f"expected string with length 1, got {val!r} with length {len(val)}"
            )

        if not isinstance(key, Coordinates | int):
            raise TypeError(f"{key!r} is not of type Coordinates or int")

        if isinstance(key, int) and key in range(self.y_len):
            self.map[key] = [val for i in range(self.x_len)]

        elif self._bounded(key):

            self.map[key.y][key.x] = val

    def replace(self, old_char: str, new_char: str) -> None:

        """Replaces all instances of old_char in the map with
        new_character."""

        if len(old_char) != 1:
            raise ValueError(
                f"expected string of length 1, got {old_char!r} of length {len(new_char)}"
            )
        if len(new_char) != 1:
            raise ValueError(
                f"expected string of length 1, got {new_char!r} of length {len(new_char)}"
            )

        coords = self.find(old_char)

        for coord in coords:
            self[coord] = new_char

@dataclass(slots=True)
class MultiMap:

    """This object provides a mechanism for a layered map.
    The first map, game_map, is the main instance with
    the secondary layer. The second map, default_map, is
    the 'background' map.

    This object provides an important method:
    - patch: replaces a character in the game_map with
    the 'background' character from default_map.

    It also supports __setitem__, which edits both the
    game_map and default_map.
    """

    game_map: GameMap
    default_map: GameMap

    def patch(self, coord: Coordinates):

        char = self.default_map[coord]
        self.game_map[coord] = char

    def __setitem__(self, coord: Coordinates, char: str):

        self.game_map[coord] = char
        self.default_map[coord] = char

class Patch(ABC):

    """Patch is an abstract base class with three main methods
    that interact with Map objects.

    - apply: applies a patch of coordinates onto another map.
    - get: using the coordinates stored in self, create a new
    patch that uses the characters of a different map.
    - __iter__: patches are iterable. Iterating on a patch
    will yield the coordinates in the patch."""

    @abstractmethod
    def apply(self, game_map: GameMap) -> None:
        ...

    @abstractmethod
    def get(self, game_map: Map) -> Patch:
        ...

    @abstractmethod
    def __iter__(self) -> Iterator[Coordinates]:
        ...

class BoxPatch(Patch):

    """A concrete implementation of the Patch ABC.
    It stores data for a box-shaped patch of characters.
    This patch can then be applied onto a Map object to
    draw the box on the object.

    This object is used mainly in the Box tool in the Editor,
    where apply draws a rectangle onto a GameMap object,
    and get is used for undo/redo purposes."""

    def __init__(self, coord_1: Coordinates, coord_2: Coordinates,
                 game_map: Map):

        """Initializes using coord_1 and coord_2, two opposite
        vertices of the box. Additionally, a Map object game_map
        must be provided to source the coordinates from."""

        x1, y1 = coord_1
        x2, y2 = coord_2

        self.coord_1 = C(min(x1, x2), min(y1, y2))
        self.coord_2 = C(max(x1, x2), max(y1, y2))

        # The only attributes required to calculate this
        # are the two previously defined ones.

        self.patch = self.__get_patch(game_map)

    def __get_patch(self, game_map: Map) -> GameMap:

        """Gets a GameMap object that represents the rectangular area
        of the patch, from the attributes self.coord_1, self.coord_2."""

        return GameMap(
            [
                row[self.row_slice] for row in game_map[self.map_slice]
            ]
        )

    @property
    def row_slice(self) -> slice:

        """Returns a slice object that is used vertically
        to source a GameMap object for the BoxPatch."""

        return slice(self.coord_1.x, self.coord_2.x+1, None)

    @property
    def map_slice(self) -> slice:

        """Returns a slice object that is used horizontally
        to source a GameMap object for the BoxPatch."""

        return slice(self.coord_1.y, self.coord_2.y+1, None)

    def apply(self, game_map: GameMap) -> None:

        """Applies the patch onto a GameMap object."""

        for coord in self:

            # Normalize coordinate so it can index the patch.
            patch_coord = coord - self.coord_1

            game_map[coord] = self.patch[patch_coord]

    def get(self, game_map: Map) -> BoxPatch:

        return BoxPatch(self.coord_1, self.coord_2, game_map)

    def __iter__(self) -> Iterator[Coordinates]:

        p = product(range(self.coord_1.x, self.coord_2.x+1),
                    range(self.coord_1.y, self.coord_2.y+1))

        for coord in p:
            yield FrozenC(*coord)

class OrganicPatch:

    """A concrete implementation of the Patch ABC.
    Unlike the BoxPatch class, this class can apply
    patches of any shape, hence the name 'organic.'
    The data for such an object is provided using
    a Map object, where NaC represents a
    transparent character. Any other character
    will be part of the Patch."""

    def __init__(self, game_map: Map):

        self.patch_dict = dict()

        for coord, char in game_map.enumerate():

            if char != Constants.NaC:
                self.patch_dict[coord.as_frozen()] = char

    def __iter__(self):

        return iter(self.patch_dict)

    def apply(self, game_map: GameMap) -> None:

        for coord, char in self.patch_dict.items():

            game_map[coord] = char

    def get(self, game_map: GameMap) -> OrganicPatch:

        length, width = game_map.x_len, game_map.y_len

        new_map = GameMap.solid(Constants.NaC, length, width)

        for coord in self:
            new_map[coord] = game_map[coord]

        return OrganicPatch(new_map)

class MemoryEfficientInfoMsgs:

    """A class that collapses the InfoMsgs class into bare minimum
    data. In a LevelData object, a GameMap object is provided
    along with data for the info messages. If the info messages
    is stored in an object such as a wrapped dictionary, where
    coordinates map to info messages, then the coordinates are obsolete
    since the coordinates are already encoded in the map itself (the
    '?' symbol). Instead, to collapse the data, the info messages
    are all stored in a *list*. These info messages are then mapped
    to their respective coordinates through the game map, as the
    info messages are put into left -> right, up -> down order.

    Conversion from MemoryEfficientInfoMsgs -> InfoMsgs is
    provided in the InfoMsgs class."""

    # no-access, doesn't contain maps.
    # suitable for serialization / save strings.

    def __init__(self,
                 msgs: list[str] | MemoryEfficientInfoMsgs | None=None
                 ) -> None:

        """Store the messages in a list."""

        if isinstance(msgs, MemoryEfficientInfoMsgs | InfoMsgs):
            self.msgs = msgs.msgs.copy()
        elif isinstance(msgs, list) and all(
                isinstance(msg, str) and len(msg) <= LevelData.MAX_INFO_WIDTH
                for msg in msgs
        ):

            self.msgs = msgs.copy()

        elif msgs is None:
            self.msgs = list()
        else:
            raise TypeError(
                "expected MemoryEfficientInfoMsgs or list[str], received "
                f"{msgs} of type {type(msgs).__name__}"
            )

    def __repr__(self) -> str:

        msgs = ", ".join(repr(msg) for msg in self.msgs)
        return f"MemoryEfficientInfoMsgs({msgs})"

    def copy(self) -> Self:

        return type(self)(self.msgs.copy())

    def __eq__(self, other) -> bool:

        return (
                isinstance(other, MemoryEfficientInfoMsgs)
                and self.msgs == other.msgs
        )

    def __iter__(self) -> Iterator[str]:

        return iter(self.msgs)

class InfoMsgs:

    """An object that wraps a dictionary, mapping coordinates
    to their info messages."""

    __slots__ = ("info_dict",)

    def __init__(self, info_dict: dict[FrozenC, str]):

        self.info_dict = info_dict

    @classmethod
    def from_memory_efficient(cls, info_msgs: MemoryEfficientInfoMsgs,
                              game_map: GameMap) -> Self:

        """Creates an InfoMsgs object from a sequential
        MemoryEfficientInfoMsgs object and a GameMap object to source
        the coordinates from. Iteration starts from the top left
        corner to the bottom right corner line by line. As an info
        character is encountered in the GameMap object ('?'), the
        next message in the MemoryEfficientInfoMsgs object is paired
        with it. Eventually, every coordinate / '?' character on the
        map is paired with a message text through this process."""

        info_coords = sorted(game_map.find("?"),
                             key=lambda coord: (-coord.y, coord.x))

        return cls(dict(zip(info_coords, info_msgs)))

    @property
    def coords(self) -> list[FrozenC]:

        # Sort coords based on up -> down, then left -> right order.
        return sorted(self.info_dict,
                      key=lambda coord: (-coord.y, coord.x))

    @property
    def msgs(self) -> list[str]:

        return [self.info_dict[coord] for coord in self.coords]


    def __repr__(self) -> str:

        coord_list = ', '.join(f'{coord!s}: {msg}'
                               for coord, msg in self.info_dict.items()
                               )

        return f"InfoMsgs({coord_list})"

    def __iter__(self) -> Iterator[str]:

        return iter(self.msgs)

    def __eq__(self, other) -> bool:

        return isinstance(other, InfoMsgs) and self.msgs == other.msgs

    def __contains__(self, coord: Coordinates) -> bool:

        return coord.as_frozen() in self.info_dict

    def get(self, key: Coordinates, default_value: Any="") -> str:

        return self.info_dict.get(key.as_frozen(), default_value)

    def __getitem__(self, key: Coordinates) -> str:

        return self.get(key)

    def __setitem__(self, key: Coordinates, msg: str) -> None:

        self.info_dict[key.as_frozen()] = msg

    def items(self) -> Iterator[tuple[FrozenC, str]]:
        return self.info_dict.items()

    def copy(self) -> Self:

        return type(self)(deepcopy(self.info_dict))

    def pop(self, key: Coordinates) -> None:

        self.info_dict.pop(key.as_frozen(), None)

class LevelID(str):

    """A subclass of str used for level IDs. This"""

@dataclass(slots=True, kw_only=True)
class LevelData:

    """A dataclass that holds all the necessary information
    for a playable level in an optimized way. This includes
    the game map, info messages, time limit, and other
    metadata such as:

    - The title and description
    - The author and date of creation
    - The points the level gives

    Note that the LevelData class is strictly keyword only,
    meaning that arguments to LevelData must be sent in this
    way:

    LevelData(title=title, author=author, desc=desc, ...)

    """

    title: str | None = "Untitled"
    author: str | None = "Unknown"

    # Dates are automatically created at time of
    # initialization if not provided.

    date: str | None = field(
        default_factory=lambda: datetime.now().strftime(
            "%m/%d/%Y, %I:%M:%S %p"
        )
    )

    desc: str | None = ""
    map: GameMap | None = field(default_factory=GameMap)
    time: int | float | None = float("inf")
    info: MemoryEfficientInfoMsgs | None = field(
        default_factory=MemoryEfficientInfoMsgs)
    points: Literal[0, 1, 2, 3, 4, 5] | None = 0

    # These are class variables that define
    # maximum values for fields.
    # These values are enforced in the Editor and during
    # initialization.

    MAX_DESC_WIDTH: ClassVar[int] = 300
    MAX_INFO_WIDTH: ClassVar[int] = 200
    MAX_TITLE_WIDTH: ClassVar[int] = 100
    MAX_AUTHOR_WIDTH: ClassVar[int] = 25
    MAX_TIME: ClassVar[int] = 1_000

    def __post_init__(self) -> None:

        """Verify that all data is valid. This is mostly important
        when loading save strings."""

        if all(x is None for x in self.as_tuple()):
            return

        if not isinstance(self.map, GameMap):
            raise TypeError(
                "expected GameMap object, received "
                f"{self.map} of type {type(self.map).__name__}"
            )

        if not (
                isinstance(self.desc, str) and
                len(self.desc) <= LevelData.MAX_DESC_WIDTH
        ):
            raise TypeError(
                f"expected str object with at most {LevelData.MAX_DESC_WIDTH:,} characters"
            )
        if not (isinstance(self.time, int) or isinstance(self.time, float)):
            raise TypeError("time is not an int or float object")

        if not (
                self.time == float("inf") or
                (0.0 < self.time <= LevelData.MAX_TIME)
        ):
            raise ValueError(
                f"time is nonpositive or above {LevelData.MAX_TIME:,} seconds"
            )
        if not (
                isinstance(self.title, str) and
                len(self.title) <= LevelData.MAX_TITLE_WIDTH
        ):
            raise TypeError(
                f"expected str object with at most {LevelData.MAX_TITLE_WIDTH:,} characters"
            )

        if not isinstance(self.info, MemoryEfficientInfoMsgs):
            raise TypeError("info is not a MemoryEfficientInfoMsgs object")
        if not isinstance(self.points, int):
            raise TypeError("points is not an integer")
        elif self.points not in range(6):
            raise ValueError("points is not an integer from 0 to 5")
        if not (
                isinstance(self.author, str) and
                0 < len(self.author) <= LevelData.MAX_AUTHOR_WIDTH
        ):
            raise TypeError(
                "expected non-empty string with at most {:,} characters".format(
                    LevelData.MAX_AUTHOR_WIDTH
                )
            )

    @property
    def start(self) -> C:

        """Returns the coordinates for the start position of a game map ('S').
        If there are no start positions, or multiple start positions, then
        an error will be raised."""

        if self == LevelData.NULL:
            return C()

        elif not self:
            raise ValueError(f"corrupted LevelData object {self}")

        start_set = self.map.find("S")

        n = len(start_set)

        if n == 0:
            raise ValueError("no start positions found.")
        elif n > 1:
            raise ValueError(
                "found multiple start positions at {}".format(
                    ', '.join(str(coord) for coord in start_set)
                ))

        return list(start_set)[0].as_normal()

    @property
    def id(self) -> str:

        """Returns an ID for a level by hashing its data using the SHA-256
        scheme. Note: the ID should NEVER be used on levels that may be
        edited, as the ID is obtained directly from the data. So,
        the ID will change before and after data. Instead, the ID should
        (and is) strictly used for levels that do not change, such as
        the main levels and public levels."""

        if self.map is None:
            raw_map_str = "None"
        else:
            raw_map_str = "".join("".join(line) for line in self.map.map)

        strs = (
            str(self.title),
            str(self.author),
            str(self.date),
            str(self.desc),
            raw_map_str,
            str(self.time),
            str(self.info),
            str(self.points)
        )

        # Remove the null byte, as this will be used
        # as a delimiter between pieces of data.

        # The null byte does not have any meaning in
        # SHA-256, so this is just a safety measure.

        binary = [
            string.encode("utf-8").replace(b"\x00", b"")
            for string in strs
        ]

        bytes_obj = b"\x00".join(binary)

        return sha256(bytes_obj).hexdigest()

    def score(self, result: Result) -> int:

        """Multiplies the points data stored in LevelData by the order
        of the result: how many things were achieved. For example,
        just winning would cause self.score to be self.points.
        Winning with a coin would multiply it by two.
        Winning with a coin and under the time limit would multiply
        it by three, etc.

        In this way, self.points only provides the bottom limit
        for what happens if you JUST win. In reality, you can gain
        even more points when you play the map."""

        return self.points * result.order

    def text_length(self, display_desc: bool) -> int:

        """Returns the number of newlines covered by the text displayed
        above the time and the map in Platformer mode.
        This takes into account things like info messages, the title
        and description, following the exact formatting patterns
        used in the Platformer mode.

        This is important as the text length dictates the exact space
        taken up by messages above the map. This allows strings to be
        padded with that many newlines, preventing the game map from
        shaking around with new messages."""

        if self == LevelData.NULL:
            return -1
        elif not self:
            raise ValueError(f"corrupted LevelData object {self}")

        # Matches the code in plat.Renderer._render.
        new_title = shorten(self.title.upper(), width=(self.map.x_len // 3),
                            placeholder="..."
                            )

        # Matches the code in plat.Renderer._render.
        formatted_desc = shorten(
            f"[{new_title!s}] {(self.desc if display_desc else '')!s}",
            width=self.map.x_len, placeholder="..."
        )

        # All possible text displayed at the top of the screen
        # in Platformer game mode.

        txts = [
            formatted_desc,
            *self.info,
            "[||] PAUSED",
            "Launch!"
        ]

        # Add the prefix 'O |', '? |', etc. you see at the top
        # of the screen in Platformer mode.
        # Also remove newlines.

        txts = map(lambda txt: f"@ | {txt}".replace("\n", ""), txts)

        # Find the maximum number of newlines any of these strings take
        # up when wrapped.

        return max(len(wrap(txt, width=self.map.x_len+2)) for txt in txts)

    def copy(self):

        """Returns a deep copied version of self.

        self.copy is an example of the date being sent
        into LevelData.__init__ rather than being
        automatically generated."""

        if self == LevelData.NULL:
            return LevelData.NULL
        elif not self:
            raise ValueError(f"corrupted LevelData object {self}")

        title, author, date, desc, map_, time, info, points = self

        return LevelData(
            title=title,
            author=author,
            date=date,
            desc=desc,
            map=map_.copy(),
            time=time,
            info=info.copy(),
            points=points
        )

    def __bool__(self):

        """A LevelData object is falsy if any of the data fields
        in the object are None."""

        return not any(attr is None for attr in self.as_tuple())

    def __eq__(self, other):

        """Two LevelData objects are equal if all their data
        fields are equal."""

        if not isinstance(other, LevelData):
            return False

        return self.as_tuple() == other.as_tuple()

    def __iter__(self):

        """Iterating through a LevelData object will just iterate
        through its data fields."""

        if not self and self != LevelData.NULL:
            raise ValueError(f"corrupted LevelData object {self}")

        return iter(self.as_tuple())

    def __repr__(self):

        """The string representation of a LevelData object
        only shows the title."""

        return f"LevelData(title={self.title!r})"

    # --- Conversions (tuple) ---

    def as_tuple(self) -> tuple:

        """Data fields as a tuple."""

        return (
            self.title,
            self.author,
            self.date,
            self.desc,
            self.map,
            self.time,
            self.info,
            self.points,
        )

    @classmethod
    def from_tuple(cls, args: tuple) -> Self:

        """Creates a LevelData object from a tuple of arguments."""

        title, author, date, desc, map_, time, info, points = args
        return cls(
            title=title,
            author=author,
            date=date,
            desc=desc,
            map=map_,
            time=time,
            info=info,
            points=points
        )

    # --- Conversions (stuple) ---

    def as_stuple(self) -> tuple:

        """Data fields as a tuple with a checksum.
        Known as a 'stuple' in this codebase, when a
        checksum is affixed to a tuple of data fields."""

        return (
            self.title,
            self.author,
            self.date,
            self.desc,
            self.map,
            self.time,
            self.info,
            self.points,
            self.id # Checksum
        )

    @classmethod
    def from_stuple(cls, args: tuple) -> Self:

        """Create a LevelData object from a stuple (see LevelData.as_stuple).
        It uses the field data to create a new instance, and then validates
        it against the checksum to ensure the data has not been tampered
        with."""

        data, checksum = args[:-1], args[-1]
        new = cls.from_tuple(data)

        if new.id != checksum:

            raise SerializationError(
                "save string was manipulated; checksum does not match"
            )
        else:
            return new

    # --- Conversions (save string) ---

    @classmethod
    def from_save_str(cls, save_str: str, /) -> Self:

        """Creates a level from a save string."""

        decoded = decompress(base64.a85decode(save_str.encode("utf-8")))

        return cls.from_stuple(pickle.loads(decoded))

    def as_save_str(self) -> str:

        """Returns the save string for a level."""

        if not self and self != LevelData.NULL:
            raise ValueError(f"corrupted LevelData object {self}")

        encoded = compress(pickle.dumps(self.as_stuple()))

        save_str = base64.a85encode(encoded)
        return save_str.decode("utf-8")

# Remember that a LevelData object is falsy if any
# of its fields are None.

# Falsy LevelData objects whose data fields are not
# ALL none are corrupted, and they will cause errors.

# However, there is a unique LevelData object with all its data
# fields as None, known as LevelData.NULL.

# This object is important since it can pass through virtually
# all functions without causing errors. For example, playing
# LevelData.NULL will not play anything. It mostly acts as a
# cancellation sentinel value.

# Examples:
# - EditorMode.edit returns NULL when a user doesn't save their work.
# - PaginateUtils.paginate_maps returns NULL when a user exits.

LevelData.NULL = LevelData(
    title=None,
    author=None,
    date=None,
    desc=None,
    map=None,
    time=None,
    info=None,
    points=None
)

class LevelDatabase:

    """An immutable, ordered database that wraps around a list
    of LevelData objects. It allows high level operations with
    multiple forms of data, such as LevelData objects,
    IDs, and save strings."""

    __slots__ = ("_levels", "_ids_to_levels")

    def __init__(self, levels: Iterable[LevelData] | None=None) -> None:

        """The LevelDatabase object internally stores two data structures,
        _levels and _ids_to_levels. _levels stores a list of LevelData
        objects. The purpose of _ids_to_levels is to map level IDs
        to their LevelData objects. """

        # Creates order
        self._levels = list(levels) or []

        # For reversing SHA-256
        self._ids_to_levels = {lvl.id: lvl for lvl in self._levels}

    @classmethod
    def from_save_strs(cls, save_strs: list[str]) -> Self:

        """Constructs a LevelDatabase from a list of save strings."""

        return cls(
            [LevelData.from_save_str(save_str) for save_str in save_strs]
        )

    @classmethod
    def from_range(cls, r: range) -> Self:

        """Constructs a LevelDatabase from a range of the GLOBAL_STRS
        dict."""

        return cls.from_save_strs([GLOBAL_STRS[i] for i in r])

    def title(self, level_id: str, /, *, default: str="Unknown") -> str:

        """Gets the title of a level from its ID."""

        try:
            return self[level_id].title
        except KeyError:
            return default

    def timelimit(self, level_id: str, /, *, default: str=float("inf")
                  ) -> int | float:

        """Gets the timelimit of a level from its ID."""

        try:
            return self[level_id].time
        except KeyError:
            return default

    def query(self, search: str) -> Self:

        """The query method fuzzy searches the database using a title.
        It returns a new database of levels that have similar titles
        to the search."""

        titles = [lvl.title for lvl in self]
        title_matches = set(get_close_matches(search, titles))

        level_matches = [lvl for lvl in self if lvl.title in title_matches]

        return type(self)(level_matches)

    def copy(self) -> Self:

        """Returns a copy of the database."""

        return type(self)(self._levels)

    def __bool__(self) -> bool:

        """Returns whether the database is not empty."""
        return bool(self._levels)

    def __len__(self) -> int:

        """Returns the length of the database."""

        return len(self._levels)

    def __iter__(self) -> Iterator[LevelData]:

        """Returns an iterator of LevelData objects."""

        return iter(self._levels)

    def __repr__(self) -> str:

        """String representation of a database."""

        return f"LevelDatabase({self._levels})"

    def __contains__(self, obj: str | LevelData) -> bool:

        """Returns whether a LevelData object or ID is in the database."""

        if isinstance(obj, str):
            return obj in self._ids_to_levels
        elif isinstance(obj, LevelData):
            return obj.id in self._ids_to_levels
        else:
            raise TypeError(f"{obj!r} is not of type str or LevelData")

    def __getitem__(self, key: int | str | slice) -> LevelData | LevelDatabase:

        """__getitem__ can either return the level at a certain index,
        the level with a certain ID, or a slice of the database."""

        if isinstance(key, int):

            if key not in range(len(self)):
                raise IndexError(
                    f"level index {key!r} out of range {len(self)}"
                )

            return self._levels[key]

        elif isinstance(key, slice):

            return type(self)(self._levels[key])

        elif isinstance(key, str):

            if key not in self:
                raise KeyError(f"no level with ID {key!r}")

            return self._ids_to_levels[key]

        else:
            raise TypeError(f"{key} is not of type int, slice, or str.")

# --- DATABASES ---

GLOBAL_DATABASE = LevelDatabase.from_range(GLOBAL_RANGE)
SHOWCASE_DATABASE = LevelDatabase.from_save_strs(SHOWCASE)
PUBLIC_DATABASE = LevelDatabase.from_save_strs(PUBLIC)