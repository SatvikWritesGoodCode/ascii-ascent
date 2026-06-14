from mainmode import MainMode

r"""       
  m   .m,   mm  mmm  mmm        m   .m,   mm .mmm,.m .,.mmm,
 ]W[ .P'T  W''[ 'W'  'W'       ]W[ .P'T  W''[]P''`]W ][''W'`
 ]W[ ]b   ]P     W    W        ]W[ ]b   ]P   ][   ]P[][  W  
 W W  TWb ][     W    W        W W  TWb ][   ]WWW ][W][  W  
 WWW    T[]b     W    W        WWW    T[]b   ][   ][]d[  W  
.W W,]mmd` Wmm[ mWm  mWm      .W W,]mmd` Wmm[]bmm,][ W[  W  
'` '` ''`   ''  '''  '''      '` '` ''`   '' ''''`'` '`  '
ASCII Ascent: A Platformer Game [Capybara Studios (C) 2026]
"""

# Create a spinoff, paste your save string here!
# Or, keep it somewhere else and directly paste it into the original program!
SAVESTR = r"""Gar&?:T0i7&Pm.JqFEroU5=f$7VUt<dX'3/5BDk3o"]!D;QW[)kXJnAS=/ELk.Pu2pO60M=D\kV$6LJaCCAQZU!R\1[Yn$3eVunhDKO@%@\GDH$SJ`e#Wgk&iT5A%+8;AErQWQ)I_V<>7n8%-O7bl`cUP[`99['F.Eg)A5H%r(5ogD!)p\J.Gj'p8?8(FrgS8&f54Q='3HlS4?S++0Tg(<3e%MG>r#ParrbVGp9]kqTqbVcO7!\RI_%LIWh\:"-;RNbDB!q[d6*\^uj$G3"`JTpr'onDmQ<\jGLok3mYn[^tA:KBGTg*k6UMfTNn0>ijp<!<t-(-E03^('ap64I`E+/@(Im8)LSaRV_dVkT8D2JOeM3nG[8I1\7lB?X5-5E#T\J2&b8E,.B6%i8MZ:KXWqp_Np^2WW6f?qqBlH,BaHMWm=*<;3g+;_"C9SPtAMjNR3+f>?no?K@*OJZ#j-5)$/i$g\njoGAHL!>U45Q9ctpDt5m*OVtJp_YjtNWC7MC+4E_NB(ZHc.J1(Qkj_b\VV)).V<$=VFiAK?iJkus7snS=QZ)NNe'oG+c!'C)b+chd^#%]$J3X7bdAdi]e:ZloKaQV+W-"oZZ4022XJH6YJ'nY&!g?'$UH%BMj/8md82CI+L8BYaQP?lMBOp\a1Id]:#K"a<QT$hRe>n]^Nntqd2,=.'O*E6ARF+_P,8;;Une\@&Ai[%PL^800I_rnb,3*f[F)+$'39(u4aZk2Il`$n`$L8c`_\6WU1P\cY?G`WS';fSPpmMa&a^`_X5J#52V$=28=PYj\9Ir<cs)"6p%otOWJ,'f<AiE+<7.BD;CuDLg8TmbS!WI\U6QL(c(5k$`2G.?VQA_4rkZ1Zqg\K9IPXi$HE6R1'?R@VRn<Z.em$n5OSWYO+Z.>!`8o'CMc=j7Ebm89pRM0AlgXX[^<&G;$#"mRBpO,io`R9.eL+m$-!E(jd1pT52U)pf8)5(\'bkQFiJd@)_:'?14MK#U-s@/sJ<Z^[AD8q1A;ir.Ns[6i)Q5VlQ;\q,X'$q^aMkD9/%BfZs4>.ArR6_8[ZDgQK!J'29d!iE&YSru*E3JX8q`5Tp(1*R2jRK8'\m9F0sA/un\Uj3\FbOg=(5kq:rmAbe"SU+=b:rR4,-k>;>5#XY$$B.4t9W+<\QX>5A+*7rQ:Cl+$]_+?]V^J$`cQdoHpO[1b3`HC4LuF)J9H_"s8F+M+_S<GZM+Aq\ujY-S)_+Z-P#9oYC<ZMqVf0CRkdR<Y$=O1T0GI't"<M;lg\('C+mClGh>*6GV99$Rt$AY5RS%Qf%f2k#)`T=R\n;P`@6$^NaZiOj#9gdP>RA0`dNdHaW\UkYj:1[TAaU[-G-lE:<U(hd>r9GbgY5/`]mAgfdPsJQWHiQ`<Ph&lfUB/9MpaHa^aXF1N6"F]tZGs8UoehRkc+qOl)m@!+`sk4Lt&1fP*,<='8FXgc=6nBK5QWk&5%J>B.L05N>Eo'kAh\%XUZ2r[;)M7KX\aP,\pNAf*AX&\@7#`R>G(O[p7dj+$qJnUT1HHlPfh)pBk^YdoGbMQ(.U&&'eCNJ<?b@S5-H26i8hl],Nf\N/1&,q$[?`1&jh0luNGXm7bRs)0FeP1-!?[1_ep$KHfktlIhml`Cf-\[?=qXqC@h.6!%K111``kars'0M]K0"nj819\UerQ-"nlZ>2Jq$9?GDE8gJc]'*6@?+'oD4-A:$M0rUG2Hcc9m7-)'t1UKj7i$4Nir<+]Ki!Smn^+-<]?MpN`L215J9-aluecNf!K;A]T_#ZIV$/pL=nC$`aqac!irqUV5E18H%7r93FSi?=`jC<lZKWNh#jD"E4X7>ZL3flq!'6#RFK+"""

# Checklist [in order]:

# - Refactor and document

# FUTURE FEATURES:
# - Portals for changing game modes
# - Blindfold mode: cannot see map as well as character

__version__ = "1.0"

if __name__ == "__main__":

    MainMode(savestr=SAVESTR).run()
