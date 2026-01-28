import hashlib
import io
import os
import pwd
from types import SimpleNamespace

import fitz
from PIL import Image
from django.conf import settings
from django.core.management import BaseCommand
from django.utils import timezone

from apps.main.models import Bazaar
from apps.parking.models import Parking
from apps.rent.models import ThingData, Thing
from apps.shop.models import Shop
from apps.stall.models import Stall
from smartbozor.security import switch_to_www_data


class Command(BaseCommand):
    DPI = 72

    def add_cut_line(self, page, dash_mm=10, line_width_pt=0.7, color=(0, 0, 0)):
        r = page.rect
        x = (r.width / 2)
        p1, p2 = (x, 0), (x, r.height)

        page.draw_line(p1=p1, p2=p2, color=color, width=line_width_pt, dashes="[10 10] 0")

    def resize_image(self, image_file, x=2):
        img = Image.open(image_file)
        width, height = img.size
        new_size = (width // x, height // x)
        resized_img = img.resize(new_size, Image.LANCZOS)
        buf = io.BytesIO()
        resized_img.save(buf, format="PNG")
        buf.seek(0)
        resized_img.close()
        return buf

    def get_sizes(self):
        a4_w_pt, a4_h_pt = fitz.paper_size("a4-l")
        a5_w_pt = 148 / 25.4 * self.DPI
        a5_h_pt = 210 / 25.4 * self.DPI

        return a4_w_pt, a4_h_pt, a5_w_pt, a5_h_pt, 0

    def create_pdf(self, load_data, save_path, save_url):
        a4_w_pt, a4_h_pt, a5_w_pt, a5_h_pt, margin_pt = self.get_sizes()
        bazaar_count = Bazaar.objects.count()

        for bazaar_idx, bazaar in enumerate(Bazaar.objects.order_by('id').all()):
            print(bazaar.name, f"[{bazaar_idx + 1} / {bazaar_count}]")

            data_list, map_fn, prefix = load_data(bazaar)
            data_hash = hashlib.sha256("-".join(sorted(map(map_fn, data_list))).encode()).hexdigest()
            file_name = f"{prefix}-{timezone.localtime().date():%Y-%m-%d}-{data_hash}.pdf"

            field_name = f"{prefix}_pdf"
            pdf_file = getattr(bazaar, field_name)
            if pdf_file:
                if pdf_file.name.endswith(f"-{data_hash}.pdf"):
                    print("\talready built")
                    continue

                if os.path.exists(pdf_file.path):
                    os.remove(pdf_file.path)

            doc = fitz.open()
            idx = -1
            for idx, row in enumerate(data_list):
                print(f"\t{prefix}: {idx + 1} / {len(data_list)}", end='\r')
                if idx % 2 == 0:
                    page = doc.new_page(width=a4_w_pt, height=a4_h_pt)
                    rect = fitz.Rect(margin_pt, margin_pt, margin_pt + a5_w_pt, margin_pt + a5_h_pt)
                else:
                    rect = fitz.Rect(margin_pt + a5_w_pt + margin_pt, margin_pt,
                                     margin_pt + a5_w_pt + margin_pt + a5_w_pt, margin_pt + a5_h_pt)

                page.insert_image(rect, stream=self.resize_image(row.qr_image_file, 4), keep_proportion=True)
                if idx % 2 == 1:
                    self.add_cut_line(page)

            if idx >= 0:
                doc.save(save_path / file_name)
                doc.close()

                setattr(bazaar, field_name, save_url + "/" + file_name)
                bazaar.save()
                print("\tsaved" + " " * 10)
            else:
                print("\tnot found")

        print()

    def load_stall_pdf_data(self, bazaar):
        stall_list = list(Stall.objects.filter(section__area__bazaar_id=bazaar.id).order_by('id').prefetch_related("section__area").all())
        def stall_map(stall):
            return f"{stall.section.area_id}-{stall.section_id}-{stall.id}"

        return stall_list, stall_map, "stall"

    def load_shop_pdf_data(self, bazaar):
        shop_list = list(Shop.objects.filter(section__area__bazaar_id=bazaar.id).order_by('id').prefetch_related("section__area").all())
        def shop_map(shop):
            return f"{shop.section.area_id}-{shop.section_id}-{shop.id}"

        return shop_list, shop_map, "shop"

    def load_rent_pdf_data(self, bazaar):
        thing_data = list(ThingData.objects.prefetch_related("thing").filter(
            bazaar_id=bazaar.id
        ).order_by('thing_id').all())

        rent_list = []
        for thd in thing_data:
            for number in range(1, thd.count + 1):
                rent_list.append(SimpleNamespace(
                    bazaar_id=bazaar.id,
                    thing_id=thd.thing_id,
                    number=number,
                    qr_image_file=Thing.get_qr_img_file(bazaar, thd.thing, number)
                ))

        def rent_map(thing):
            return f"{thing.bazaar_id}-{thing.thing_id}-{thing.number}"

        return rent_list, rent_map, "rent"

    def load_parking_pdf_data(self, bazaar):
        parking_list = list(Parking.objects.filter(
            bazaar_id=bazaar.id
        ).order_by("id").all())

        def parking_map(parking):
            return f"{parking.id}"

        return parking_list, parking_map, "parking"


    def handle(self, *args, **options):
        switch_to_www_data()

        save_url = "qr-codes/pdf"
        save_path = settings.MEDIA_ROOT / save_url
        if not os.path.exists(save_path):
            os.makedirs(save_path)

        self.create_pdf(self.load_stall_pdf_data, save_path, save_url)
        self.create_pdf(self.load_shop_pdf_data, save_path, save_url)
        self.create_pdf(self.load_rent_pdf_data, save_path, save_url)
        self.create_pdf(self.load_parking_pdf_data, save_path, save_url)

