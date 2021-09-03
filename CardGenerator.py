import os
import math
import yaml
import sys
import argparse

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
class Fonts(object):
    styles = {}
    # Scaling factor between the font size and its actual height in mm
    FONT_SCALE = None

    def __init__(self):
        self.paragraph_styles = StyleSheet1()


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

    def set_font(self, canvas, section):
        canvas.setFont(
            self.styles[section][0], self.styles[section][1] * self.FONT_SCALE
        )
        return self.styles[section][1]

    def __init__(self):
        super().__init__()
        pdfmetrics.registerFont(
            TTFont("Universal Serif", os.path.join("fonts", "Universal Serif.ttf"))
        )
        pdfmetrics.registerFont(
            TTFont("ScalySans", os.path.join("fonts", "ScalySans.ttf"))
        )
        pdfmetrics.registerFont(
            TTFont("ScalySansItalic", os.path.join("fonts", "ScalySans-Italic.ttf"))
        )
        pdfmetrics.registerFont(
            TTFont("ScalySansBold", os.path.join("fonts", "ScalySans-Bold.ttf"))
        )
        pdfmetrics.registerFont(
            TTFont(
                "ScalySansBoldItalic", os.path.join("fonts", "ScalySans-BoldItalic.ttf")
            )
        )

        addMapping("ScalySans", 0, 0, "ScalySans")  # normal
        addMapping("ScalySans", 0, 1, "ScalySansItalic")  # italic
        addMapping("ScalySans", 1, 0, "ScalySansBold")  # bold
        addMapping("ScalySans", 1, 1, "ScalySansBoldItalic")  # italic and bold

        self.paragraph_styles.add(
            ParagraphStyle(
                name="text",
                fontName=self.styles["text"][0],
                fontSize=self.styles["text"][1] * self.FONT_SCALE,
                leading=self.styles["text"][1] * self.FONT_SCALE + 0.5 * mm,
                spaceBefore=1 * mm,
            )
        ),
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

    def set_font(self, canvas, section):
        canvas.setFont(
            self.styles[section][0], self.styles[section][1] * self.FONT_SCALE
        )
        return self.styles[section][1]

    def __init__(self):
        super().__init__()
        pdfmetrics.registerFont(
            TTFont(
                "ModestoExpanded", os.path.join("fonts", "ModestoExpanded-Regular.ttf")
            )
        )
        pdfmetrics.registerFont(
            TTFont("ModestoTextLight", os.path.join("fonts", "ModestoText-Light.ttf"))
        )
        pdfmetrics.registerFont(
            TTFont(
                "ModestoTextLightItalic",
                os.path.join("fonts", "ModestoText-LightItalic.ttf"),
            )
        )
        pdfmetrics.registerFont(
            TTFont("ModestoTextBold", os.path.join("fonts", "ModestoText-Bold.ttf"))
        )
        pdfmetrics.registerFont(
            TTFont(
                "ModestoTextBoldItalic",
                os.path.join("fonts", "ModestoText-BoldItalic.ttf"),
            )
        )

        addMapping("ModestoTextLight", 0, 0, "ModestoTextLight")  # normal
        addMapping("ModestoTextLight", 0, 1, "ModestoTextLightItalic")  # italic
        addMapping("ModestoTextLight", 1, 0, "ModestoTextBold")  # bold
        addMapping("ModestoTextLight", 1, 1, "ModestoTextBoldItalic")  # italic and bold

        self.paragraph_styles.add(
            ParagraphStyle(
                name="text",
                fontName=self.styles["text"][0],
                fontSize=self.styles["text"][1] * self.FONT_SCALE,
                leading=self.styles["text"][1] * self.FONT_SCALE + 0.5 * mm,
                spaceBefore=1 * mm,
            )
        ),
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
            canvas.setFillColor("red")
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


class Modifier(object):
    @classmethod
    def from_ability_score(cls, value):
        if value < 1 or value > 30:
            raise ValueError("Ability scores must be between 1 and 30 inclusive")
        return cls(math.floor((value - 10) / 2))

    def __init__(self, value):
        value = int(value)
        if value < -5 or value > 10:
            raise ValueError(
                "Ability score modifiers must be between -5 and +10 inclusive"
            )
        self.value = value

    def __str__(self):
        if self.value <= 0:
            return "+{}".format(self.value)
        else:
            return "-{}".format(self.value)


class TemplateTooSmall(Exception):
    pass


class CardLayout(ABC):
    CARD_CORNER_DIAMETER = 3 * mm
    BACKGROUND_CORNER_DIAMETER = 2 * mm
    LOGO_WIDTH = 42 * mm
    STANDARD_BORDER = 2.5 * mm
    TEXT_MARGIN = 2 * mm
    BASE_WIDTH = 63 * mm
    BASE_HEIGHT = 89 * mm
    BORDER_COLOR = "red"
    TITLE_BAR_HEIGHT = 4.8 * mm

    # These must be set by sub classes
    WIDTH = None
    HEIGHT = None
    BORDER_FRONT = ()
    BORDER_BACK = ()

    def __init__(
        self,
        title,
        subtitle,
        artist,
        image_path,
        background="background.png",
        border_color="red",
        fonts=FreeFonts(),
    ):
        self.frames = []
        self.FRONT_MARGINS = tuple([x + 1 * mm for x in self.BORDER_FRONT])

        self.title = title
        self.subtitle = subtitle
        self.artist = artist
        self.fonts = fonts
        self.background_image_path = background

        self.front_image_path = os.path.abspath(image_path)
        # Figure out front orientation
        self.front_orientation = best_orientation(
            self.front_image_path, self.WIDTH, self.HEIGHT
        )

        self.elements = []

    def set_size(self, canvas):
        canvas.setPageSize((self.WIDTH * 2, self.HEIGHT))

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
        try:
            current_frame = next(frames)
        except StopIteration:
            return

        # Draw the elements
        while len(self.elements) > 0:
            element = self.elements[0]
            try:
                if type(element) == LineDivider:
                    
                    # Don't place a Line Divider if there is nothing after it
                    if len(self.elements) == 1:
                        del self.elements[0]
                        break;

                    available_height = (
                        current_frame._y
                        - current_frame._y1p
                        - self.elements[1].getSpaceBefore()
                    )
                    available_width = current_frame._getAvailableWidth()
                    _, line_height = element.wrap(available_width, 0xFFFFFFFF)
                    _, next_height = self.elements[1].wrap(available_width, 0xFFFFFFFF)

                    # Dont draw it if it will be the last thing on the frame
                    if available_height < line_height + next_height:
                        try:
                            current_frame = next(frames)
                        except StopIteration:
                            raise LayoutError()
                        del self.elements[0]
                        continue

                result = current_frame.add(element, canvas)
                # current_frame.drawBoundary(canvas)
                # Could not draw into current frame
                if result == 0:
                    raise LayoutError()
                del self.elements[0]
            # Frame is full, get next frame
            except LayoutError:
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
        self._draw_single_border(canvas, 0, self.WIDTH, self.HEIGHT)

        # Parchment background
        self._draw_single_background(
            canvas,
            0,
            self.BORDER_FRONT,
            self.WIDTH,
            self.HEIGHT,
            self.front_orientation,
        )

        # Set card orientation
        if self.front_orientation == Orientation.TURN90:
            canvas.rotate(90)
            canvas.translate(0, -self.WIDTH)
            width = self.HEIGHT
            height = self.WIDTH
        else:
            width = self.WIDTH
            height = self.HEIGHT

        # D&D logo
        dnd_logo = svg2rlg("logo.svg")
        if dnd_logo is not None:
            factor = self.LOGO_WIDTH / dnd_logo.width
            dnd_logo.width *= factor
            dnd_logo.height *= factor
            dnd_logo.scale(factor, factor)
            logo_margin = (self.BORDER_FRONT[Border.TOP] - dnd_logo.height) / 2
            renderPDF.draw(
                dnd_logo,
                canvas,
                (width - self.LOGO_WIDTH) / 2,
                height - self.BORDER_FRONT[Border.TOP] + logo_margin,
            )

        # Titles
        canvas.setFillColor("black")
        title_height = self.fonts.set_font(canvas, "title")
        canvas.drawCentredString(
            width * 0.5, self.FRONT_MARGINS[Border.BOTTOM], self.title.upper()
        )

        # Artist
        if self.artist:
            canvas.setFillColor("white")
            artist_font_height = self.fonts.set_font(canvas, "artist")
            canvas.drawCentredString(
                width / 2,
                self.BORDER_FRONT[Border.BOTTOM] - artist_font_height - 1 * mm,
                "Artist: {}".format(self.artist),
            )

        # Image
        image_bottom = self.FRONT_MARGINS[Border.BOTTOM] + title_height + 1 * mm
        canvas.drawImage(
            self.front_image_path,
            self.FRONT_MARGINS[Border.LEFT],
            image_bottom,
            width=width
            - self.FRONT_MARGINS[Border.LEFT]
            - self.FRONT_MARGINS[Border.RIGHT],
            height=height - image_bottom - self.FRONT_MARGINS[Border.TOP],
            preserveAspectRatio=True,
            mask="auto",
        )

        canvas.restoreState()

    def _draw_back(self, canvas):
        # Draw red border
        self._draw_single_border(canvas, self.WIDTH, self.WIDTH, self.HEIGHT)

        # Parchment background
        self._draw_single_background(
            canvas, self.WIDTH, self.BORDER_BACK, self.WIDTH, self.HEIGHT
        )

        # Title
        canvas.setFillColor("black")
        title_font_height = self.fonts.set_font(canvas, "title")
        title_line_bottom = (
            self.HEIGHT - self.BORDER_BACK[Border.TOP] - self.TITLE_BAR_HEIGHT
        )
        title_bottom = (
            title_line_bottom + (self.TITLE_BAR_HEIGHT - title_font_height) / 2
        )
        canvas.drawCentredString(
            self.WIDTH + self.BASE_WIDTH / 2, title_bottom, self.title.upper()
        )

        # Subtitle
        subtitle_line_bottom = title_line_bottom - self.STANDARD_BORDER
        canvas.setFillColor(self.BORDER_COLOR)
        canvas.rect(
            self.WIDTH,
            subtitle_line_bottom,
            self.BASE_WIDTH,
            self.STANDARD_BORDER,
            stroke=0,
            fill=1,
        )

        canvas.setFillColor("white")
        subtitle_font_height = self.fonts.set_font(canvas, "subtitle")
        subtitle_bottom = (
            subtitle_line_bottom + (self.STANDARD_BORDER - subtitle_font_height) / 2
        )
        canvas.drawCentredString(
            self.WIDTH + self.BASE_WIDTH / 2, subtitle_bottom, self.subtitle
        )

    def _draw_single_border(self, canvas, x, width, height):
        canvas.saveState()
        if type(self.BORDER_COLOR) == str:
            canvas.setFillColor(self.BORDER_COLOR)
        else:
            canvas.setFillColorRGB(
                self.BORDER_COLOR[0] / 255,
                self.BORDER_COLOR[1] / 255,
                self.BORDER_COLOR[2] / 255,
            )
        canvas.roundRect(
            x, 0, width, height, self.CARD_CORNER_DIAMETER, stroke=0, fill=1
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
    WIDTH = CardLayout.BASE_WIDTH
    HEIGHT = CardLayout.BASE_HEIGHT
    BORDER_FRONT = (
        CardLayout.STANDARD_BORDER,
        CardLayout.STANDARD_BORDER,
        7 * mm,
        7 * mm,
    )
    BORDER_BACK = (
        CardLayout.STANDARD_BORDER,
        CardLayout.STANDARD_BORDER,
        9.2 * mm,
        1.7 * mm,
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        frame = Frame(
            self.WIDTH + self.BORDER_BACK[Border.LEFT],
            self.BORDER_BACK[Border.BOTTOM],
            self.BASE_WIDTH
            - self.BORDER_BACK[Border.LEFT]
            - self.BORDER_BACK[Border.RIGHT],
            self.HEIGHT
            - self.BORDER_BACK[Border.TOP]
            - self.TITLE_BAR_HEIGHT
            - self.STANDARD_BORDER
            - self.BORDER_BACK[Border.BOTTOM],
            leftPadding=self.TEXT_MARGIN,
            bottomPadding=self.TEXT_MARGIN,
            rightPadding=self.TEXT_MARGIN,
            topPadding=1 * mm,
            showBoundary=True,
        )
        self.frames.append(frame)


class LargeCard(CardLayout):
    WIDTH = CardLayout.BASE_WIDTH * 2
    HEIGHT = CardLayout.BASE_HEIGHT

    BORDER_FRONT = (3.5 * mm, 3.5 * mm, 7 * mm, 7 * mm)
    BORDER_BACK = (4 * mm, 4 * mm, 8.5 * mm, 3 * mm)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        left_frame = Frame(
            self.WIDTH + self.BORDER_BACK[Border.LEFT],
            self.BORDER_BACK[Border.BOTTOM],
            self.BASE_WIDTH - self.BORDER_BACK[Border.LEFT] - self.STANDARD_BORDER / 2,
            self.HEIGHT
            - self.BORDER_BACK[Border.TOP]
            - self.TITLE_BAR_HEIGHT
            - self.STANDARD_BORDER
            - self.BORDER_BACK[Border.BOTTOM],
            leftPadding=self.TEXT_MARGIN,
            bottomPadding=self.TEXT_MARGIN,
            rightPadding=self.TEXT_MARGIN,
            topPadding=1 * mm,
        )
        right_frame = Frame(
            self.WIDTH * 1.5 + self.STANDARD_BORDER / 2,
            self.BORDER_BACK[Border.BOTTOM],
            self.BASE_WIDTH - self.BORDER_BACK[Border.LEFT] - self.STANDARD_BORDER / 2,
            self.HEIGHT
            - self.BORDER_BACK[Border.BOTTOM]
            - self.BORDER_BACK[Border.TOP],
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
        canvas.setFillColor(self.BORDER_COLOR)
        canvas.rect(
            self.WIDTH * 1.5 - self.STANDARD_BORDER / 2,
            0,
            self.STANDARD_BORDER,
            self.HEIGHT,
            stroke=0,
            fill=1,
        )


class EpicCard(LargeCard):
    HEIGHT = CardLayout.BASE_WIDTH * 2


class MonsterCardLayout(CardLayout):

    # These must be set by subclasses
    CHALLENGE_BOTTOM = None
    SOURCE_LOCATION = []

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
        attributes=None,
        abilities=None,
        actions=None,
        reactions=None,
        *args,
        **kwargs
    ):
        super().__init__(title, subtitle, artist, image_path, *args, **kwargs)

        self.armor_class = armor_class
        self.max_hit_points = max_hit_points
        self.speed = speed

        # Modifieres
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

        self.challenge_rating = challenge_rating
        self.experience_points = experience_points
        self.source = source

    def _draw_back(self, canvas):
        super()._draw_back(canvas)

        # Challenge
        self.fonts.set_font(canvas, "challenge")
        canvas.drawString(
            self.WIDTH + self.BORDER_FRONT[Border.LEFT],
            self.CHALLENGE_BOTTOM,
            "Challenge {} ({} XP)".format(
                self.challenge_rating, self.experience_points
            ),
        )
        ### Source
        self.fonts.set_font(canvas, "text")
        canvas.drawString(*self.SOURCE_LOCATION, self.source)

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
        line_width = self.BASE_WIDTH - self.BORDER_BACK[Border.LEFT]
        self.elements.append(
            LineDivider(
                width=line_width,
                xoffset=-self.TEXT_MARGIN,
                fill_color=self.BORDER_COLOR,
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
                "<i>{}:</i> {}".format(heading, body),
                self.fonts.paragraph_styles["text"],
            )
            self.elements.append(paragraph)

        # Divider 2
        self.elements.append(
            LineDivider(
                width=line_width,
                xoffset=-self.TEXT_MARGIN,
                fill_color=self.BORDER_COLOR,
            )
        )

        # Actions
        title = Paragraph("ACTIONS", self.fonts.paragraph_styles["action_title"])
        first_action = True
        for heading, body in (self.actions or {}).items():
            paragraph = Paragraph(
                "<i><b>{}:</b></i> {}".format(heading, body),
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
                    fill_color=self.BORDER_COLOR,
                )
            )

            title = Paragraph("REACTIONS", self.fonts.paragraph_styles["action_title"])
            first_reaction = True
            for heading, body in (self.reactions or {}).items():
                paragraph = Paragraph(
                    "<i><b>{}:</b></i> {}".format(heading, body),
                    self.fonts.paragraph_styles["text"],
                )
                if first_reaction:
                    element = KeepTogether([title, paragraph])
                    first_reaction = False
                else:
                    element = paragraph
                self.elements.append(element)


class MonsterCardSmall(SmallCard, MonsterCardLayout):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.CHALLENGE_BOTTOM = 5.5 * mm
        self.SOURCE_LOCATION = (self.WIDTH + self.BORDER_BACK[Border.LEFT], 3 * mm)


class MonsterCardLarge(LargeCard, MonsterCardLayout):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.CHALLENGE_BOTTOM = (
            self.BORDER_BACK[Border.BOTTOM] - self.fonts.styles["challenge"][1]
        ) / 2
        self.SOURCE_LOCATION = (
            self.WIDTH * 1.5 + self.STANDARD_BORDER / 2,
            self.CHALLENGE_BOTTOM,
        )


class MonsterCardEpic(EpicCard, MonsterCardLayout):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.CHALLENGE_BOTTOM = (
            self.BORDER_BACK[Border.BOTTOM] - self.fonts.styles["challenge"][1]
        ) / 2
        self.SOURCE_LOCATION = (
            self.WIDTH * 1.5 + self.STANDARD_BORDER / 2,
            self.CHALLENGE_BOTTOM,
        )


class CardGenerator(ABC):

    sizes = []  # Set by subclass

    def __init__(self, *args, **kwargs):
        self._args = args
        self._kwargs = kwargs

    def draw(self, canvas):
        # TODO: Find a way to clear the page not just draw over it
        for size in self.sizes:
            try:
                card_layout = size(*self._args, **self._kwargs)
                card_layout.draw(canvas)
                break
            except TemplateTooSmall:
                pass


class MonsterCard(CardGenerator):
    sizes = [MonsterCardSmall, MonsterCardLarge, MonsterCardEpic]


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
    parser.add_argument("input", help="Path to input YAML file", action="store")
    parser.add_argument(
        "-f",
        "--fonts",
        help="What fonts to use when generating cards",
        action="store",
        default="free",
        choices=["free", "accurate"],
        dest="fonts",
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

    canvas = canvas.Canvas(
        args.output_path, pagesize=(SmallCard.WIDTH * 4, SmallCard.HEIGHT)
    )

    with open(args.input, "r") as stream:
        try:
            entries = yaml.load(stream, Loader=yaml.SafeLoader)
        except yaml.YAMLError as exc:
            print(exc)
            exit()

    for entry in entries:
        if args.type == "monster":
            card = MonsterCard(
                entry["title"],
                entry["subtitle"],
                entry.get("artist", None),
                entry["image_path"],
                entry["armor_class"],
                entry["max_hit_points"],
                entry["speed"],
                entry["strength"],
                entry["dexterity"],
                entry["constitution"],
                entry["intelligence"],
                entry["wisdom"],
                entry["charisma"],
                entry["challenge_rating"],
                entry["experience_points"],
                entry["source"],
                entry["attributes"],
                entry.get("abilities", None),
                entry.get("actions", None),
                entry.get("reactions", None),
                fonts=fonts,
            )

        card.draw(canvas)
        canvas.showPage()
    canvas.save()