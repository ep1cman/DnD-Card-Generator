import os
import math
import yaml
import sys
import argparse
import pathlib

from enum import Enum, IntEnum
from abc import ABC
from PIL import Image

from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase.ttfonts import TTFError
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas
from reportlab.graphics import renderPDF
from reportlab.platypus import Frame, Paragraph, Table, TableStyle
from reportlab.platypus.flowables import Flowable
from reportlab.lib.styles import ParagraphStyle, StyleSheet1
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.fonts import addMapping
from reportlab.platypus.doctemplate import LayoutError
from svglib.svglib import svg2rlg


ASSET_DIR = pathlib.Path(__file__).parent.resolve() / "assets"


# Returns the best orientation for the given image aspect ration
def best_orientation(image_path, card_width, card_height):
    image = Image.open(image_path)
    image_width, image_height = image.size
    if (image_width > image_height) == (card_width > card_height):
        return Orientation.NORMAL
    else:
        return Orientation.TURN90


# TODO: Clean up the font object, it seems a bit crude
# TODO: Also manage colours
class Fonts(ABC):
    styles = {}
    # Scaling factor between the font size and its actual height in mm
    FONT_SCALE = None
    FONT_DIR = ASSET_DIR / "fonts"

    def __init__(self):
        self._register_fonts()
        self.paragraph_styles = StyleSheet1()
        self.paragraph_styles.add(
            ParagraphStyle(
                name="text",
                fontName=self.styles["text"][0],
                fontSize=self.styles["text"][1] * self.FONT_SCALE,
                leading=self.styles["text"][1] * self.FONT_SCALE + 0.5 * mm,
                spaceBefore=1 * mm,
            )
        )
        self.paragraph_styles.add(
            ParagraphStyle(
                name="legendary_action",
                fontName=self.styles["text"][0],
                fontSize=self.styles["text"][1] * self.FONT_SCALE,
                leading=self.styles["text"][1] * self.FONT_SCALE + 0.5 * mm,
                spaceBefore=0,
            )
        )
        self.paragraph_styles.add(
            ParagraphStyle(
                name="modifier",
                fontName=self.styles["text"][0],
                fontSize=self.styles["text"][1] * self.FONT_SCALE,
                leading=self.styles["text"][1] * self.FONT_SCALE + 0.5 * mm,
                alignment=TA_CENTER,
            )
        )
        self.paragraph_styles.add(
            ParagraphStyle(
                name="action_title",
                fontName=self.styles["modifier_title"][0],
                fontSize=self.styles["modifier_title"][1] * self.FONT_SCALE,
                leading=self.styles["modifier_title"][1] * self.FONT_SCALE + 0.5 * mm,
                spaceBefore=1 * mm,
            )
        )
        self.paragraph_styles.add(
            ParagraphStyle(
                name="modifier_title",
                fontName=self.styles["modifier_title"][0],
                fontSize=self.styles["modifier_title"][1] * self.FONT_SCALE,
                leading=self.styles["modifier_title"][1] * self.FONT_SCALE + 0.5 * mm,
                alignment=TA_CENTER,
            )
        )

    def set_font(self, canvas, section, custom_scale=1.0):
        canvas.setFont(
            self.styles[section][0],
            self.styles[section][1] * self.FONT_SCALE * custom_scale,
        )
        return self.styles[section][1]

    def _register_fonts(self):
        raise NotImplemented


class FreeFonts(Fonts):
    FONT_SCALE = 1.41

    styles = {
        "title": ("Universal Serif", 2.5 * mm, "black"),
        "subtitle": ("ScalySans", 1.5 * mm, "white"),
        "challenge": ("Universal Serif", 2.25 * mm, "black"),
        "heading": ("ScalySansBold", 1.5 * mm, "black"),
        "text": ("ScalySans", 1.5 * mm, "black"),
        "artist": ("ScalySans", 1.25 * mm, "white"),
        "modifier_title": ("Universal Serif", 1.5 * mm, "black"),
    }

    def _register_fonts(self):
        pdfmetrics.registerFont(
            TTFont("Universal Serif", self.FONT_DIR / "Universal Serif.ttf")
        )
        pdfmetrics.registerFont(TTFont("ScalySans", self.FONT_DIR / "ScalySans.ttf"))
        pdfmetrics.registerFont(
            TTFont("ScalySansItalic", self.FONT_DIR / "ScalySans-Italic.ttf")
        )
        pdfmetrics.registerFont(
            TTFont("ScalySansBold", self.FONT_DIR / "ScalySans-Bold.ttf")
        )
        pdfmetrics.registerFont(
            TTFont("ScalySansBoldItalic", self.FONT_DIR / "ScalySans-BoldItalic.ttf")
        )

        addMapping("ScalySans", 0, 0, "ScalySans")  # normal
        addMapping("ScalySans", 0, 1, "ScalySansItalic")  # italic
        addMapping("ScalySans", 1, 0, "ScalySansBold")  # bold
        addMapping("ScalySans", 1, 1, "ScalySansBoldItalic")  # italic and bold


class AccurateFonts(Fonts):
    FONT_SCALE = 1.41

    styles = {
        "title": ("ModestoExpanded", 2.5 * mm, "black"),
        "subtitle": ("ModestoTextLight", 1.5 * mm, "white"),
        "challenge": ("ModestoExpanded", 2.25 * mm, "black"),
        "heading": ("ModestoTextBold", 1.5 * mm, "black"),
        "text": ("ModestoTextLight", 1.5 * mm, "black"),
        "artist": ("ModestoTextLight", 1.25 * mm, "white"),
        "modifier_title": ("ModestoExpanded", 1.5 * mm, "black"),
    }

    def _register_fonts(self):
        pdfmetrics.registerFont(
            TTFont("ModestoExpanded", self.FONT_DIR / "ModestoExpanded-Regular.ttf")
        )
        pdfmetrics.registerFont(
            TTFont("ModestoTextLight", self.FONT_DIR / "ModestoText-Light.ttf")
        )
        pdfmetrics.registerFont(
            TTFont(
                "ModestoTextLightItalic",
                self.FONT_DIR / "ModestoText-LightItalic.ttf",
            )
        )
        pdfmetrics.registerFont(
            TTFont("ModestoTextBold", self.FONT_DIR / "ModestoText-Bold.ttf")
        )
        pdfmetrics.registerFont(
            TTFont(
                "ModestoTextBoldItalic",
                self.FONT_DIR / "ModestoText-BoldItalic.ttf",
            )
        )

        addMapping("ModestoTextLight", 0, 0, "ModestoTextLight")  # normal
        addMapping("ModestoTextLight", 0, 1, "ModestoTextLightItalic")  # italic
        addMapping("ModestoTextLight", 1, 0, "ModestoTextBold")  # bold
        addMapping("ModestoTextLight", 1, 1, "ModestoTextBoldItalic")  # italic and bold


# Draws a line across the frame, unless it is at the top of the frame, in which
# case nothing is drawn
class LineDivider(Flowable):
    def __init__(
        self,
        xoffset=0,
        width=None,
        fill_color="red",
        line_height=0.25 * mm,
        spacing=1 * mm,
    ):
        self.xoffset = xoffset
        self.width = width
        self.fill_color = fill_color
        self.spacing = spacing
        self.line_height = line_height
        self.height = self.line_height + self.spacing

    def _at_top(self):
        at_top = False
        frame = getattr(self, "_frame", None)
        if frame:
            at_top = getattr(frame, "_atTop", None)
        return at_top

    def wrap(self, *args):
        if self._at_top():
            return (0, 0)
        else:
            return (self.width, self.height)

    def draw(self):
        if not self._at_top():
            canvas = self.canv
            canvas.setFillColor(self.fill_color)
            canvas.rect(self.xoffset, 0, self.width, self.line_height, stroke=0, fill=1)


class KeepTogether(Flowable):
    def __init__(self, flowables):
        self.flowables = flowables
        self._available_height = None
        self._available_width = None

    def wrap(self, aW, aH):
        self._available_width = aW
        self._available_height = aH

        height = 0
        width = 0
        for flowable in self.flowables:
            w, h = flowable.wrap(aW, 0xFFFFFFFF)
            height += flowable.getSpaceBefore()
            height += h
            height += flowable.getSpaceAfter()
            if w > width:
                width = w
        return width, height

    def drawOn(self, canvas, x, y, _sW=0):
        y -= self.flowables[0].getSpaceBefore()
        for flowable in self.flowables[::-1]:
            y += flowable.getSpaceBefore()
            width, height = flowable.wrap(self._available_width, self._available_height)
            flowable.drawOn(canvas, x, y, _sW=_sW)
            y += height
            y += flowable.getSpaceAfter()
            self._available_height -= (
                flowable.getSpaceBefore() + height + flowable.getSpaceBefore()
            )


class Orientation(Enum):
    NORMAL = 1
    TURN90 = 2


class Border(IntEnum):
    LEFT = 0
    RIGHT = 1
    BOTTOM = 2
    TOP = 3


class TemplateTooSmall(Exception):
    pass


class CardLayout(ABC):
    CARD_CORNER_DIAMETER = 3 * mm
    BACKGROUND_CORNER_DIAMETER = 2 * mm
    LOGO_WIDTH = 42 * mm
    STANDARD_BORDER = 2.5 * mm
    STANDARD_MARGIN = 1.0 * mm
    TEXT_MARGIN = 2 * mm
    BASE_WIDTH = 63 * mm
    BASE_HEIGHT = 89 * mm
    TITLE_BAR_HEIGHT = 4.8 * mm

    def __init__(
        self,
        title,
        subtitle,
        artist,
        image_path,
        background=ASSET_DIR / "background.png",
        border_color="red",
        border_front=(0, 0, 0, 0),  # uninitialized
        border_back=(0, 0, 0, 0),  # uninitialized
        width=0,  # uninitialized
        height=0,  # uninitialized
        bleed=0,  # uninitialized
        fonts=FreeFonts(),
    ):
        self.frames = []
        self.title = title
        self.subtitle = subtitle
        self.artist = artist
        self.fonts = fonts
        self.background_image_path = background
        self.border_color = border_color
        self.border_front = tuple([v + bleed for v in border_front])
        self.border_back = tuple([v + bleed for v in border_back])
        self.width = width + 2 * bleed
        self.height = height + 2 * bleed
        self.bleed = bleed
        self.front_image_path = os.path.abspath(image_path)
        self.front_orientation = best_orientation(
            self.front_image_path, self.width, self.height
        )
        self.elements = []
        self.front_margins = tuple(
            [x + self.STANDARD_MARGIN for x in self.border_front]
        )

    def set_size(self, canvas):
        canvas.setPageSize((self.width * 2, self.height))

    def draw(self, canvas):
        self.set_size(canvas)
        self._draw_front(canvas)
        self._draw_back(canvas)
        self.fill_frames(canvas)
        self._draw_frames(canvas)

    def fill_frames(self, canvas):
        pass

    def _draw_frames(self, canvas):
        frames = iter(self.frames)
        current_frame = next(frames)

        # Draw the elements
        while len(self.elements) > 0:
            element = self.elements.pop(0)

            if type(element) == LineDivider:

                # Don't place a Line Divider if there is nothing after it
                if len(self.elements) == 0:
                    break

                # Caluclate how much space is left
                available_width = current_frame._getAvailableWidth()
                available_height = current_frame._y - current_frame._y1p

                # Calculate how much heigh is required for the line and the next element
                _, line_height = element.wrap(available_width, 0xFFFFFFFF)
                _, next_height = self.elements[0].wrap(available_width, 0xFFFFFFFF)

                # Dont draw it if it will be the last thing on the frame
                if available_height < line_height + next_height:
                    continue

            # DEBUG: Draw frame boundary
            # current_frame.drawBoundary(canvas)

            # Could not draw into current frame
            result = current_frame.add(element, canvas)
            if result == 0:
                # We couldn't draw the element, so put it back
                self.elements.insert(0, element)
                try:
                    current_frame = next(frames)
                # No more frames
                except StopIteration:
                    break

        # If there are undrawn elements, raise an error
        if len(self.elements) > 0:
            raise TemplateTooSmall("Template too small")

    def _draw_front(self, canvas):
        canvas.saveState()

        # Draw red border
        self._draw_single_border(canvas, 0, self.width, self.height)

        # Parchment background
        self._draw_single_background(
            canvas,
            0,
            self.border_front,
            self.width,
            self.height,
            self.front_orientation,
        )

        # Set card orientation
        if self.front_orientation == Orientation.TURN90:
            canvas.rotate(90)
            canvas.translate(0, -self.width)
            width = self.height
            height = self.width
        else:
            width = self.width
            height = self.height

        # D&D logo
        dnd_logo = svg2rlg(ASSET_DIR / "logo.svg")
        if dnd_logo is not None:
            factor = self.LOGO_WIDTH / dnd_logo.width
            dnd_logo.width *= factor
            dnd_logo.height *= factor
            dnd_logo.scale(factor, factor)
            logo_margin = (
                self.border_front[Border.TOP] - self.bleed - dnd_logo.height
            ) / 2
            renderPDF.draw(
                dnd_logo,
                canvas,
                (width - self.LOGO_WIDTH) / 2,
                height - self.border_front[Border.TOP] + logo_margin,
            )

        # Titles
        custom_scale = (
            min(1.0, 20 / len(self.title)) if isinstance(self, SmallCard) else 1.0
        )
        canvas.setFillColor("black")
        title_height = self.fonts.set_font(canvas, "title", custom_scale)
        canvas.drawCentredString(
            width * 0.5, self.front_margins[Border.BOTTOM], self.title.upper()
        )

        # Artist
        if self.artist:
            canvas.setFillColor("white")
            artist_font_height = self.fonts.set_font(canvas, "artist")
            canvas.drawCentredString(
                width / 2,
                self.border_front[Border.BOTTOM] - artist_font_height - 1 * mm,
                "Artist: {}".format(self.artist),
            )

        # Image
        image_bottom = self.front_margins[Border.BOTTOM] + title_height + 1 * mm
        canvas.drawImage(
            self.front_image_path,
            self.front_margins[Border.LEFT],
            image_bottom,
            width=width
            - self.front_margins[Border.LEFT]
            - self.front_margins[Border.RIGHT],
            height=height - image_bottom - self.front_margins[Border.TOP],
            preserveAspectRatio=True,
            mask="auto",
        )

        canvas.restoreState()

    def _draw_back(self, canvas):
        # Draw red border
        self._draw_single_border(canvas, self.width, self.width, self.height)

        # Parchment background
        self._draw_single_background(
            canvas, self.width, self.border_back, self.width, self.height
        )

        # Title
        custom_scale = min(1.0, 20 / len(self.title))
        canvas.setFillColor("black")
        title_font_height = self.fonts.set_font(canvas, "title", custom_scale)
        title_line_bottom = self.frames[0]._y2 + self.STANDARD_BORDER
        title_bottom = (
            title_line_bottom + (self.TITLE_BAR_HEIGHT - title_font_height) / 2
        )
        title_center = (self.frames[0]._x1 + self.frames[0]._x2) / 2
        canvas.drawCentredString(title_center, title_bottom, self.title.upper().strip())

        # Subtitle
        subtitle_line_bottom = title_line_bottom - self.STANDARD_BORDER
        canvas.setFillColor(self.border_color)
        canvas.rect(
            self.frames[0]._x1,
            self.frames[0]._y2,
            self.frames[0]._width,
            self.STANDARD_BORDER,
            stroke=0,
            fill=1,
        )

        canvas.setFillColor("white")
        subtitle_font_height = self.fonts.set_font(canvas, "subtitle")
        subtitle_bottom = (
            subtitle_line_bottom + (self.STANDARD_BORDER - subtitle_font_height) / 2
        )
        canvas.drawCentredString(title_center, subtitle_bottom, self.subtitle)

    def _draw_single_border(self, canvas, x, width, height):
        canvas.saveState()
        canvas.setFillColor(self.border_color)
        canvas.roundRect(
            x,
            0,
            width,
            height,
            max(self.CARD_CORNER_DIAMETER - self.bleed, 0.0 * mm),
            stroke=0,
            fill=1,
        )
        canvas.restoreState()

    def _draw_single_background(
        self, canvas, x, margins, width, height, orientation=Orientation.NORMAL
    ):
        canvas.saveState()

        clipping_mask = canvas.beginPath()

        if orientation == Orientation.TURN90:
            clipping_mask.roundRect(
                x + margins[Border.BOTTOM],
                margins[Border.LEFT],
                width - margins[Border.TOP] - margins[Border.BOTTOM],
                height - margins[Border.RIGHT] - margins[Border.LEFT],
                self.BACKGROUND_CORNER_DIAMETER,
            )
        else:
            clipping_mask.roundRect(
                x + margins[Border.LEFT],
                margins[Border.BOTTOM],
                width - margins[Border.RIGHT] - margins[Border.LEFT],
                height - margins[Border.TOP] - margins[Border.BOTTOM],
                self.BACKGROUND_CORNER_DIAMETER,
            )
        canvas.clipPath(clipping_mask, stroke=0, fill=0)

        canvas.drawImage(
            self.background_image_path, x, 0, width=width, height=height, mask=None
        )

        canvas.restoreState()


class SmallCard(CardLayout):
    def __init__(
        self,
        width=CardLayout.BASE_WIDTH,
        height=CardLayout.BASE_HEIGHT,
        border_front=(2.5 * mm, 2.5 * mm, 7.0 * mm, 7.0 * mm),
        border_back=(2.5 * mm, 2.5 * mm, 9.2 * mm, 1.7 * mm),
        **kwargs
    ):
        super().__init__(
            width=width,
            height=height,
            border_front=border_front,
            border_back=border_back,
            **kwargs
        )

        frame = Frame(
            self.width + self.border_back[Border.LEFT],
            self.border_back[Border.BOTTOM],
            self.width - self.border_back[Border.LEFT] - self.border_back[Border.RIGHT],
            self.height
            - self.border_back[Border.TOP]
            - self.TITLE_BAR_HEIGHT
            - self.STANDARD_BORDER
            - self.border_back[Border.BOTTOM],
            leftPadding=self.TEXT_MARGIN,
            bottomPadding=self.TEXT_MARGIN,
            rightPadding=self.TEXT_MARGIN,
            topPadding=1 * mm,
            showBoundary=True,
        )
        self.frames.append(frame)


class LargeCard(CardLayout):
    def __init__(
        self,
        width=CardLayout.BASE_WIDTH * 2,
        height=CardLayout.BASE_HEIGHT,
        border_front=(3.5 * mm, 3.5 * mm, 7.0 * mm, 7.0 * mm),
        border_back=(4.0 * mm, 4.0 * mm, 8.5 * mm, 3.0 * mm),
        **kwargs
    ):
        super().__init__(
            width=width,
            height=height,
            border_front=border_front,
            border_back=border_back,
            **kwargs
        )

        left_frame = Frame(
            self.width + self.border_back[Border.LEFT],
            self.border_back[Border.BOTTOM],
            self.width / 2 - self.border_back[Border.LEFT] - self.STANDARD_BORDER / 2,
            self.height
            - self.border_back[Border.TOP]
            - self.TITLE_BAR_HEIGHT
            - self.STANDARD_BORDER
            - self.border_back[Border.BOTTOM],
            leftPadding=self.TEXT_MARGIN,
            bottomPadding=self.TEXT_MARGIN,
            rightPadding=self.TEXT_MARGIN,
            topPadding=1 * mm,
        )
        right_frame = Frame(
            self.width * 1.5 + self.STANDARD_BORDER / 2,
            self.border_back[Border.BOTTOM],
            self.width / 2 - self.border_back[Border.LEFT] - self.STANDARD_BORDER / 2,
            self.height
            - self.border_back[Border.BOTTOM]
            - self.border_back[Border.TOP],
            leftPadding=self.TEXT_MARGIN,
            bottomPadding=self.TEXT_MARGIN,
            rightPadding=self.TEXT_MARGIN,
            topPadding=1 * mm,
            showBoundary=True,
        )
        self.frames.append(left_frame)
        self.frames.append(right_frame)

    def draw(self, canvas):
        super().draw(canvas)
        canvas.setFillColor(self.border_color)
        canvas.rect(
            self.width * 1.5 - self.STANDARD_BORDER / 2,
            0,
            self.STANDARD_BORDER,
            self.height,
            stroke=0,
            fill=1,
        )


class EpicCard(LargeCard):
    def __init__(
        self,
        height=CardLayout.BASE_WIDTH * 2,
        border_back=(4.0 * mm, 4.0 * mm, 6.5 * mm, 3.0 * mm),
        **kwargs
    ):
        super().__init__(height=height, border_back=border_back, **kwargs)

        # Card is square, don't rotate it
        self.front_orientation = Orientation.NORMAL


class SuperEpicCard(EpicCard):
    def __init__(self, height=CardLayout.BASE_WIDTH * 3, **kwargs):
        super().__init__(height=height, **kwargs)


class MonsterCardLayout(CardLayout):
    def __init__(
        self,
        title,
        subtitle,
        artist,
        image_path,
        armor_class,
        max_hit_points,
        speed,
        strength,
        dexterity,
        constitution,
        intelligence,
        wisdom,
        charisma,
        challenge_rating,
        experience_points,
        source,
        attributes,
        abilities,
        actions,
        reactions,
        legendary,
        **kwargs
    ):
        super().__init__(title, subtitle, artist, image_path, **kwargs)
        self.armor_class = armor_class
        self.max_hit_points = max_hit_points
        self.speed = speed
        self.strength = strength
        self.dexterity = dexterity
        self.constitution = constitution
        self.intelligence = intelligence
        self.wisdom = wisdom
        self.charisma = charisma
        self.attributes = attributes
        self.abilities = abilities
        self.actions = actions
        self.reactions = reactions
        self.legendary = legendary
        self.challenge_rating = challenge_rating
        self.experience_points = experience_points
        self.source = source

    def _draw_back(self, canvas):
        super()._draw_back(canvas)

        # Challenge
        self.fonts.set_font(canvas, "challenge")
        canvas.drawString(
            self.width + self.border_front[Border.LEFT],
            self.challenge_bottom,
            "Challenge {} ({} XP)".format(
                self.challenge_rating, self.experience_points
            ),
        )
        ### Source
        self.fonts.set_font(canvas, "text")
        canvas.drawString(*self.source_location, self.source)

    def fill_frames(self, canvas):
        top_stats = [
            [
                Paragraph(
                    "<b>AC:</b> {}<br/><b>Speed:</b> {}".format(
                        self.armor_class, self.speed
                    ),
                    self.fonts.paragraph_styles["text"],
                ),
                Paragraph(
                    "<b>HP:</b> {}".format(self.max_hit_points),
                    self.fonts.paragraph_styles["text"],
                ),
            ]
        ]
        ts = TableStyle(
            [
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ]
        )
        t = Table(top_stats, style=ts, spaceBefore=1 * mm)
        self.elements.append(t)

        # Modifiers
        abilities = ["STR", "DEX", "CON", "INT", "WIS", "CHA"]
        modifiers = [
            self.strength,
            self.dexterity,
            self.constitution,
            self.intelligence,
            self.wisdom,
            self.charisma,
        ]
        # if modifiers are (int), e.g. 13, then automatically reformat as "13 (+1)"
        modifiers = [
            (m if isinstance(m, str) else "%d (%+d)" % (m, math.floor((m - 10) / 2)))
            for m in modifiers
        ]
        modifier_table_data = [
            [
                Paragraph(a, self.fonts.paragraph_styles["modifier_title"])
                for a in abilities
            ],
            [Paragraph(m, self.fonts.paragraph_styles["modifier"]) for m in modifiers],
        ]

        t = Table(
            modifier_table_data,
            [self.BASE_WIDTH / (len(abilities) + 1)] * 5,
            style=ts,
            spaceBefore=1 * mm,
        )
        self.elements.append(t)

        # Divider 1
        line_width = self.frames[0]._width
        self.elements.append(
            LineDivider(
                width=line_width,
                xoffset=-self.TEXT_MARGIN,
                fill_color=self.border_color,
            )
        )

        # Attributes
        # TODO: Handle list attributes
        text = ""
        for heading, body in (self.attributes or {}).items():
            text += "<b>{}:</b> {}<br/>".format(heading, body)
        self.elements.append(Paragraph(text, self.fonts.paragraph_styles["text"]))

        # Abilities
        for heading, body in (self.abilities or {}).items():
            paragraph = Paragraph(
                "<i><b>{}.</b></i> {}".format(heading, body),
                self.fonts.paragraph_styles["text"],
            )
            self.elements.append(paragraph)

        # Divider 2
        self.elements.append(
            LineDivider(
                width=line_width,
                xoffset=-self.TEXT_MARGIN,
                fill_color=self.border_color,
            )
        )

        # Actions
        title = Paragraph("ACTIONS", self.fonts.paragraph_styles["action_title"])
        first_action = True
        for heading, body in (self.actions or {}).items():
            paragraph = Paragraph(
                "<i><b>{}.</b></i> {}".format(heading, body),
                self.fonts.paragraph_styles["text"],
            )
            if first_action:
                element = KeepTogether([title, paragraph])
                first_action = False
            else:
                element = paragraph
            self.elements.append(element)

        if self.reactions is not None:
            # Divider 3
            self.elements.append(
                LineDivider(
                    width=line_width,
                    xoffset=-self.TEXT_MARGIN,
                    fill_color=self.border_color,
                )
            )

            title = Paragraph("REACTIONS", self.fonts.paragraph_styles["action_title"])
            first_reaction = True
            for heading, body in (self.reactions or {}).items():
                paragraph = Paragraph(
                    "<i><b>{}.</b></i> {}".format(heading, body),
                    self.fonts.paragraph_styles["text"],
                )
                if first_reaction:
                    element = KeepTogether([title, paragraph])
                    first_reaction = False
                else:
                    element = paragraph
                self.elements.append(element)

        if self.legendary is not None:
            self.elements.append(
                LineDivider(
                    width=line_width,
                    xoffset=-self.TEXT_MARGIN,
                    fill_color=self.border_color,
                )
            )

            title = Paragraph(
                "LEGENDARY ACTIONS", self.fonts.paragraph_styles["action_title"]
            )
            first_legendary = True
            for entry in self.legendary or []:
                if type(entry) == str:
                    paragraph = Paragraph(
                        entry,
                        self.fonts.paragraph_styles["text"],
                    )
                elif type(entry) == dict:
                    paragraph = Paragraph(
                        "<i><b>{}.</b></i> {}".format(*list(entry.items())[0]),
                        self.fonts.paragraph_styles["legendary_action"],
                    )
                else:
                    TypeError(
                        'Legendary action cannot be type "{}"'.format(type(entry))
                    )

                if first_legendary:
                    element = KeepTogether([title, paragraph])
                    first_legendary = False
                else:
                    element = paragraph
                self.elements.append(element)


class MonsterCardSmall(SmallCard, MonsterCardLayout):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.challenge_bottom = 5.5 * mm + self.bleed
        self.source_location = (
            self.width + self.border_back[Border.LEFT],
            3 * mm + self.bleed,
        )


class MonsterCardLarge(LargeCard, MonsterCardLayout):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.challenge_bottom = (
            self.border_back[Border.BOTTOM]
            - self.bleed
            - self.fonts.styles["challenge"][1]
        ) / 2 + self.bleed
        self.source_location = (
            self.width * 1.5 + self.STANDARD_BORDER / 2,
            self.challenge_bottom,
        )


class MonsterCardEpic(EpicCard, MonsterCardLarge):
    pass


class MonsterCardSuperEpic(SuperEpicCard, MonsterCardLarge):
    pass


class CardGenerator(ABC):
    sizes = []  # Set by subclass

    def __init__(self, *args, **kwargs):
        self._args = args
        self._kwargs = kwargs

    def draw(self, canvas):
        for size in self.sizes:
            try:
                card_layout = size(*self._args, **self._kwargs)
                card_layout.draw(canvas)
                canvas.showPage()
                break
            except TemplateTooSmall:
                # Reset the page
                canvas._restartAccumulators()
                canvas.init_graphics_state()
                canvas.state_stack = []
        else:
            print("Could not fit {}".format(self._kwargs["title"]))


class MonsterCard(CardGenerator):
    sizes = [MonsterCardSmall, MonsterCardLarge, MonsterCardEpic, MonsterCardSuperEpic]


if __name__ == "__main__":

    parser = argparse.ArgumentParser(description="Generate D&D cards.")
    parser.add_argument(
        "-t",
        "--type",
        help="What type of cards to generate",
        action="store",
        default="monster",
        choices=["monster"],
        dest="type",
    )
    parser.add_argument(
        "-o",
        "--out",
        help="Output file path",
        action="store",
        default="cards.pdf",
        dest="output_path",
        metavar="output_path",
    )
    parser.add_argument(
        "input",
        help="Path to input YAML file",
        action="store",
        type=lambda p: pathlib.Path(p).absolute(),
    )
    parser.add_argument(
        "-f",
        "--fonts",
        help="What fonts to use when generating cards",
        action="store",
        default="free",
        choices=["free", "accurate"],
        dest="fonts",
    )
    parser.add_argument(
        "-b",
        "--bleed",
        help="How many millimeters of print bleed radius to add around each card.",
        action="store",
        default=0,
        type=lambda b: float(b) * mm,
    )

    args = parser.parse_args()

    fonts = None
    if args.fonts == "accurate":
        try:
            fonts = AccurateFonts()
        except TTFError:
            raise Exception(
                "Failed to load accurate fonts, are you sure you used the correct file names?"
            )
    else:
        fonts = FreeFonts()

    canvas = canvas.Canvas(args.output_path, pagesize=(0, 0))

    with open(args.input, "r") as stream:
        try:
            entries = yaml.load(stream, Loader=yaml.SafeLoader)
        except yaml.YAMLError as exc:
            print(exc)
            exit()

    for entry in entries:
        if args.type == "monster":

            image_path = None
            if "image_path" in entry:
                image_path = pathlib.Path(entry["image_path"])
                if not image_path.is_absolute():
                    image_path = (args.input.parent / image_path).absolute()
                if not image_path.exists():
                    raise ValueError(
                        "Invalid `image_path` in `{}`: {}".format(
                            entry["title"], entry["image_path"]
                        )
                    )
            else:
                image_path = ASSET_DIR / "placeholder.png"

            card = MonsterCard(
                title=entry["title"],
                subtitle=entry["subtitle"],
                artist=entry.get("artist", None),
                image_path=image_path,
                armor_class=entry["armor_class"],
                max_hit_points=entry["max_hit_points"],
                speed=entry["speed"],
                strength=entry["strength"],
                dexterity=entry["dexterity"],
                constitution=entry["constitution"],
                intelligence=entry["intelligence"],
                wisdom=entry["wisdom"],
                charisma=entry["charisma"],
                challenge_rating=entry["challenge_rating"],
                experience_points=entry["experience_points"],
                source=entry["source"],
                attributes=entry["attributes"],
                abilities=entry.get("abilities", None),
                actions=entry.get("actions", None),
                reactions=entry.get("reactions", None),
                legendary=entry.get("legendary", None),
                fonts=fonts,
                border_color=entry.get("color", "red"),
                bleed=args.bleed,
            )

        card.draw(canvas)
    canvas.save()
