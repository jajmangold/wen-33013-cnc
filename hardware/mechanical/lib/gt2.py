"""GT2 pulley tooth profile.

The Gates GT2 (2 mm) pulley groove is approximated the way every open-source
pulley generator does it: a circular groove of radius GROOVE_R, GROOVE_H deep
below the tooth OD, blended into the OD land by a tip fillet of radius TIP_R.
Well inside belt tolerance and it machines/prints cleanly.
"""
import math

import Part
from FreeCAD import Vector


def _polar(r, a):
    return Vector(r * math.cos(a), r * math.sin(a), 0.0)


def tooth_profile_wire(teeth, pitch, pld, groove_r, tip_r, groove_h):
    """Closed wire of the full toothed outer profile, in the XY plane."""
    pd = pitch * teeth / math.pi
    ro = pd / 2.0 - pld                 # tooth tip (OD) radius
    rc = ro - groove_h + groove_r       # groove arc centre radius
    rf = ro - tip_r                     # tip fillet centre radius

    # angular offset of a tip-fillet centre from its groove centre
    cosphi = (rc * rc + rf * rf - (groove_r + tip_r) ** 2) / (2.0 * rc * rf)
    phi = math.acos(max(-1.0, min(1.0, cosphi)))

    step = 2.0 * math.pi / teeth
    if 2.0 * phi >= step:
        raise ValueError("tip fillets overlap - profile constants are wrong")

    edges = []
    for i in range(teeth):
        th = i * step
        cg = _polar(rc, th)

        for sign in (-1, +1):
            cf = _polar(rf, th + sign * phi)
            p_od = _polar(ro, th + sign * phi)          # fillet <-> OD land
            d = cg.sub(cf)
            t_groove = cf.add(d.normalize().multiply(tip_r))  # fillet <-> groove
            m = cf.add(p_od.sub(cf).normalize()
                       .add(t_groove.sub(cf).normalize())
                       .normalize().multiply(tip_r))
            if sign < 0:
                edges.append(Part.Arc(p_od, m, t_groove).toShape())
                t_minus = t_groove
            else:
                deep = _polar(rc - groove_r, th)
                edges.append(Part.Arc(t_minus, deep, t_groove).toShape())
                edges.append(Part.Arc(t_groove, m, p_od).toShape())
                land_from = th + phi

        # OD land across to the next groove
        land_to = (i + 1) * step - phi
        edges.append(Part.Arc(_polar(ro, land_from),
                              _polar(ro, (land_from + land_to) / 2.0),
                              _polar(ro, land_to)).toShape())

    wire = Part.Wire(Part.__sortEdges__(edges))
    if not wire.isClosed():
        raise ValueError("tooth profile wire did not close")
    return wire, pd, ro
