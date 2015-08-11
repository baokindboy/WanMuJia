# -*- coding: utf-8 -*-
import json
import time
import random

from flask import current_app
from flask.ext.login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

from app import db, login_manager
from app.constants import VENDOR_REMINDS, DISTRIBUTOR_REMINDS
from app.utils import convert_url
from app.utils.redis import redis_get, redis_set
from .permission import privilege_id_prefix, vendor_id_prefix, distributor_id_prefix, user_id_prefix


class Property(object):
    """
    This class is used to flush property attributes.

    class UserAddress(db.Model):
        # other attributes
        user_id = db.Column(db.Integer)

    class User(db.Model, Property):
        # other attributes

        _flush = {'address': lambda x: UserAddress.query.filter_by(user_id=x.id).first()}

        @property
        def address(self):
            return self.get_or_flush('address')

    If sometime user._address is inconsistent with database
    user.flush('address')
    """

    _flush = {}

    def flush(self, *attrs):
        for attr in attrs:
            setattr(self, '_%s' % attr, self._flush[attr](self))

    def get_or_flush(self, attr):
        real_attr = '_%s' % attr
        if not getattr(self, real_attr, None):
            self.flush(attr)
        return getattr(self, real_attr, None)


class BaseUser(UserMixin):
    # id
    id = db.Column(db.Integer, primary_key=True)
    # 哈希后的密码
    password_hash = db.Column('password', db.String(128), nullable=False)
    # 手机号码
    mobile = db.Column(db.CHAR(11), unique=True, nullable=False)
    # 邮箱
    email = db.Column(db.String(64), unique=True, nullable=False)
    # 邮箱是否已验证
    email_confirmed = db.Column(db.Boolean, default=False, nullable=False)
    # 注册时间
    created = db.Column(db.Integer, default=time.time, nullable=False)

    id_prefix = ''
    REMINDS = None

    def __init__(self, password, mobile, email):
        self.password = password
        self.mobile = mobile
        self.email = email

    @property
    def password(self):
        raise AttributeError('password is not a readable attribute')

    @password.setter
    def password(self, password):
        self.password_hash = generate_password_hash(password)

    def verify_password(self, password):
        return check_password_hash(self.password_hash, password)

    def get_id(self):
        return u'%s%s' % (self.id_prefix, self.id)

    @property
    def reminds(self):
        reminds = redis_get(self.REMINDS, self.id)
        if reminds:
            reminds = json.loads(reminds)
        else:
            reminds = {}
        return reminds


class User(BaseUser, db.Model):
    __tablename__ = 'users'
    # 用户名
    username = db.Column(db.Unicode(20), unique=True, nullable=False)

    id_prefix = user_id_prefix

    def __init__(self, password, mobile, email, username=u''):
        super(User, self).__init__(password, mobile, email)
        self.username = username if username else self.generate_username()

    @staticmethod
    def generate_username():
        prefix = u'用户'
        while 1:
            username = u'%s%s' % (prefix, random.randint(100000, 999999))
            if not User.query.filter_by(username=username).first():
                return username


class Collection(db.Model):
    __tablename__ = 'collections'
    # id
    id = db.Column(db.Integer, primary_key=True)
    # 用户id
    user_id = db.Column(db.Integer, nullable=False)
    # 商品id
    item_id = db.Column(db.Integer, nullable=False)
    # 创建时间
    created = db.Column(db.Integer, default=time.time, nullable=False)

    def __init__(self, user_id, item_id):
        self.user_id = user_id
        self.item_id = item_id


class Order(db.Model):
    __tablename__ = 'orders'
    # id
    id = db.Column(db.Integer, primary_key=True)
    # 用户id
    user_id = db.Column(db.Integer, nullable=False)
    # 用户收货地址id
    user_address_id = db.Column(db.Integer, nullable=False)
    # 商家id
    distributor_id = db.Column(db.Integer, nullable=False)
    # 商品id
    item_id = db.Column(db.Integer, nullable=False)
    # 创建时间
    created = db.Column(db.Integer, default=time.time, nullable=False)
    # 定金
    deposit = db.Column(db.Integer, nullable=False)
    # 定金已支付
    deposit_payed = db.Column(db.Boolean, default=False, nullable=False)
    # 价格
    price = db.Column(db.Integer, nullable=False)
    # 钱款已支付
    price_payed = db.Column(db.Boolean, default=False, nullable=False)


class Vendor(BaseUser, db.Model, Property):
    __tablename__ = 'vendors'
    # logo图片
    logo = db.Column(db.String(255), default='', nullable=False)
    # 法人真实姓名
    agent_name = db.Column(db.Unicode(10), nullable=False)
    # 法人身份证号码
    agent_identity = db.Column(db.CHAR(18), nullable=False)
    # 法人身份证正面图片
    agent_identity_front = db.Column(db.String(255), default='', nullable=False)
    # 法人身份证反面图片
    agent_identity_back = db.Column(db.String(255), default='', nullable=False)
    # 品牌厂家名称
    name = db.Column(db.Unicode(30), unique=True, nullable=False)
    # 营业执照期限
    license_limit = db.Column(db.CHAR(10), default='2035/07/19', nullable=False)
    # 营业执照副本扫描件
    license_image = db.Column(db.String(255), default='', nullable=False)
    # 联系人
    contact = db.Column(db.String(30), default=u'', nullable=False)
    # 联系电话
    telephone = db.Column(db.CHAR(15), nullable=False)
    # 简介
    introduction = db.Column(db.Unicode(30), default=u'', nullable=False)
    # 已通过审核
    confirmed = db.Column(db.Boolean, default=False, nullable=False)
    # 审核通过时间
    confirmed_time = db.Column(db.Integer, default=0, nullable=False)
    # 审核信息
    reject_message = db.Column(db.Unicode(100), default=u'', nullable=False)
    # 审核已回绝
    rejected = db.Column(db.Boolean, default=False, nullable=False)
    # 已初始化账号
    initialized = db.Column(db.Boolean, default=True, nullable=False)
    # 商品上传权限
    item_permission = db.Column(db.Boolean, default=False, nullable=False)

    id_prefix = vendor_id_prefix
    REMINDS = VENDOR_REMINDS

    _flush = {
        'address': lambda x: VendorAddress.query.filter_by(vendor_id=x.id).limit(1).first(),
        'logo': lambda x: convert_url(x.logo)
    }
    _logo = None
    _address = None

    def __init__(self, password, mobile, email, agent_name, agent_identity, name, license_limit, telephone):
        super(Vendor, self).__init__(password, mobile, email)
        self.agent_name = agent_name
        self.agent_identity = agent_identity
        self.name = name
        self.license_limit = license_limit
        self.telephone = telephone

    @property
    def address(self):
        return self.get_or_flush('address')

    @property
    def logo_url(self):
        return self.get_or_flush('logo')

    @property
    def statistic(self):
        return {
            'items': Item.query.filter_by(vendor_id=self.id, is_deleted=False).count(),
            'distributors': Distributor.query.filter_by(vendor_id=self.id, is_revoked=False).count()
        }

    def push_confirm_reminds(self, status, reject_message=''):
        link = None
        if status == 'success':
            message = '您的认证信息已通过审核, 快来上传商品吧!'
        elif status == 'warning':
            message = '您的认证信息将在3个工作日内审核'
        else:
            message = '您的认证信息尚未能通过审核 %s' % reject_message
            link = {'text': '重新填写', 'href': '/vendor/reconfirm'}
        reminds = {'confirm': [{'message': message, 'type': status, 'link': link}]}
        redis_set(self.REMINDS, self.id, json.dumps(reminds), 3600 * 24 * 3)

    @staticmethod
    def generate_fake():
        from faker.factory import Factory
        from random import randint
        zh_fake = Factory.create('zh-CN')
        fake = Factory.create()
        vendors = []
        for i in range(100):
            vendor = Vendor(
                "14e1b600b1fd579f47433b88e8d85291", zh_fake.phone_number(), fake.email(), zh_fake.name(),
                zh_fake.random_number(18), '%s%s' % (zh_fake.company(), zh_fake.random_number(3)),
                zh_fake.random_number(2), zh_fake.phone_number())
            db.session.add(vendor)
            vendors.append(vendor)
        db.session.commit()
        districts = District.query.all()
        for vendor in vendors:
            vendor_address = VendorAddress(vendor.id, districts[randint(0, len(districts))].cn_id, zh_fake.address())
            db.session.add(vendor_address)
        db.session.commit()


class Distributor(BaseUser, db.Model, Property):
    __tablename__ = 'distributors'
    # 登录名
    username = db.Column(db.Unicode(20), nullable=False)
    # 生产商 id
    vendor_id = db.Column(db.Integer, nullable=False)
    # 商家名称
    name = db.Column(db.Unicode(30), nullable=False)
    # 联系电话
    contact_telephone = db.Column(db.String(30), default='', nullable=False)
    # 联系手机
    contact_mobile = db.Column(db.CHAR(11), default='', nullable=False)
    # 联系人
    contact = db.Column(db.Unicode(10), nullable=False)
    # 已解约
    is_revoked = db.Column(db.Boolean, default=False, nullable=False)

    # 手机号码
    mobile = None
    # 邮箱
    email = db.Column(db.String(64), default='', nullable=False)

    id_prefix = distributor_id_prefix
    REMINDS = DISTRIBUTOR_REMINDS

    _flush = {
        'vendor': lambda x: Vendor.query.get(x.vendor_id),
        'address': lambda x: DistributorAddress.query.filter_by(distributor_id=x.id).limit(1).first(),
        'revocation': lambda x: DistributorRevocation.query.filter_by(distributor_id=x.id).first()
    }
    _vendor = None
    _address = None
    _revocation = None

    def __init__(self, username, password, vendor_id, name, contact_mobile, contact_telephone, contact):
        super(Distributor, self).__init__(password, mobile='', email='')
        self.username = username
        self.vendor_id = vendor_id
        self.name = name
        self.contact_telephone = contact_telephone
        self.contact_mobile = contact_mobile
        self.contact = contact

    @property
    def vendor(self):
        return self.get_or_flush('vendor')

    @property
    def address(self):
        return self.get_or_flush('address')

    @property
    def revocation(self):
        return self.get_or_flush('revocation')

    @property
    def revocation_state(self):
        revocation = self.revocation
        if not revocation:
            return ''
        elif revocation.pending:
            return 'pending'
        elif revocation.is_revoked:
            return 'revoked'
        else:
            return 'rejected'

    def push_register_reminds(self):
        status = 'warning'
        message = '请牢记您的登录用户名: %s' % self.username
        reminds = {'confirm': [{'message': message, 'type': status, 'link': None}]}
        redis_set(self.REMINDS, self.id, json.dumps(reminds), 3600 * 24 * 3)

    @staticmethod
    def generate_username():
        from random import randint
        for i in range(10):
            username = randint(10000000, 99999999)
            if not Distributor.query.filter_by(username=username).limit(1).first():
                return username
        return False


class DistributorRevocation(db.Model, Property):
    __tablename__ = 'distributor_revocations'
    id = db.Column(db.Integer, primary_key=True)
    # 创建时间
    created = db.Column(db.Integer, default=time.time, nullable=False)
    # 商家id
    distributor_id = db.Column(db.Integer, nullable=False)
    # 解约合同照片
    contract = db.Column(db.String(255), default='', nullable=False)
    # 待审核
    pending = db.Column(db.Boolean, default=True, nullable=False)
    # 已解约
    is_revoked = db.Column(db.Boolean, default=False, nullable=False)

    def __init__(self, distributor_id, contract):
        self.distributor_id = distributor_id
        self.contract = contract

    _flush = {
        'distributor': lambda x: Distributor.query.get(x.distributor_id)
    }
    _distributor = None

    @property
    def distributor(self):
        return self.get_or_flush('distributor')


class Item(db.Model, Property):
    __tablename__ = 'items'
    # 商品id
    id = db.Column(db.Integer, primary_key=True)
    # 创建时间
    created = db.Column(db.Integer, default=time.time, nullable=False)
    # 厂家id
    vendor_id = db.Column(db.Integer, nullable=False)
    # 商品名称
    item = db.Column(db.Unicode(20), nullable=False)
    # 指导价格
    price = db.Column(db.Integer, nullable=False)
    # 材料 id
    material_id = db.Column(db.Integer, nullable=False)
    # 商品二级分类id
    second_category_id = db.Column(db.Integer, nullable=False)
    # 长度 cm
    length = db.Column(db.Integer, nullable=False)
    # 宽度 cm
    width = db.Column(db.Integer, nullable=False)
    # 高度 cm
    height = db.Column(db.Integer, nullable=False)
    # 烘干 id
    stove_id = db.Column(db.Integer, nullable=False)
    # 雕刻 id
    carve_id = db.Column(db.Integer, nullable=False)
    # 打磨砂纸 id
    sand_id = db.Column(db.Integer, nullable=False)
    # 涂饰 id
    paint_id = db.Column(db.Integer, nullable=False)
    # 装饰 id
    decoration_id = db.Column(db.Integer, nullable=False)
    # 二级场景 id
    second_scene_id = db.Column(db.Integer, nullable=False)
    # 产品寓意
    story = db.Column(db.Unicode(5000), default=u'', nullable=False)
    # 已删除
    is_deleted = db.Column(db.Boolean, default=False, nullable=False)

    _flush = {
        'vendor': lambda x: Vendor.query.get(x.vendor_id),
        'second_category': lambda x: SecondCategory.query.get(x.second_category_id).second_category,
        'images': lambda x: ItemImage.query.filter_by(item_id=x.id, is_deleted=False).order_by(ItemImage.sort,
                                                                                               ItemImage.created)
    }
    _vendor = None
    _second_category = None
    _images = None

    def __init__(self, vendor_id, item, price, material_id, second_category_id, second_scene_id, length, width, height,
                 stove_id, carve_id, sand_id, paint_id, decoration_id, story=u''):
        self.vendor_id = vendor_id
        self.item = item
        self.price = price
        self.material_id = material_id
        self.second_category_id = second_category_id
        self.second_scene_id = second_scene_id
        self.length = length
        self.width = width
        self.height = height
        self.stove_id = stove_id
        self.carve_id = carve_id
        self.sand_id = sand_id
        self.paint_id = paint_id
        self.decoration_id = decoration_id
        self.story = story

    def stock_count(self):
        return sum([stock.stock for stock in Stock.query.filter(Stock.item_id == self.id, Stock.stock > 0)])

    def get_tenon_id(self):
        return [item_tenon.tenon_id for item_tenon in ItemTenon.query.filter_by(item_id=self.id)]

    def in_stock_distributors(self):
        distributors = db.session.query(Distributor).filter(Stock.item_id == self.id, Stock.stock > 0,
                                                            Stock.distributor_id == Distributor.id,
                                                            Distributor.is_revoked is False)
        return distributors

    @property
    def vendor(self):
        return self.get_or_flush('vendor')

    @property
    def second_category(self):
        return self.get_or_flush('second_category')

    @property
    def images(self):
        return self.get_or_flush('images')


class ItemImage(db.Model, Property):
    __tablename__ = 'item_images'
    id = db.Column(db.Integer, primary_key=True)
    item_id = db.Column(db.Integer, nullable=False)
    path = db.Column(db.String(255), nullable=False)
    hash = db.Column(db.String(32), nullable=False)
    sort = db.Column(db.Integer, nullable=False)
    created = db.Column(db.Integer, default=time.time, nullable=False)
    is_deleted = db.Column(db.Boolean, default=False, nullable=False)
    filename = db.Column(db.Unicode(30), nullable=False)

    def __init__(self, item_id, image, image_hash, filename, sort):
        self.item_id = item_id
        self.path = image
        self.hash = image_hash
        self.filename = filename
        self.sort = sort

    _flush = {
        'item': lambda x: Item.query.get(x.item_id),
        'url': lambda x: convert_url(x.path)
    }
    _item = None
    _url = None

    @property
    def item(self):
        return self.get_or_flush('item')

    def get_vendor_id(self):
        return self.item.vendor_id

    @property
    def url(self):
        return self.get_or_flush('url')


class Stock(db.Model):
    __tablename__ = 'stocks'
    id = db.Column(db.Integer, primary_key=True)
    item_id = db.Column(db.Integer, nullable=False)
    distributor_id = db.Column(db.Integer, nullable=False)
    stock = db.Column(db.Integer, default=0, nullable=False)

    def __init__(self, item_id, distributor_id, stock):
        self.item_id = item_id
        self.distributor_id = distributor_id
        self.stock = stock


class FirstCategory(db.Model):
    __tablename__ = 'first_categories'
    id = db.Column(db.Integer, primary_key=True)
    first_category = db.Column(db.Unicode(10), nullable=False)

    @staticmethod
    def generate_fake():
        first_categories = [u'椅凳类', u'桌案类', u'床榻类', u'柜架类', u'其他类']
        for first_category in first_categories:
            db.session.add(FirstCategory(first_category=first_category))
        db.session.commit()


class SecondCategory(db.Model):
    __tablename__ = 'second_categories'
    id = db.Column(db.Integer, primary_key=True)
    second_category = db.Column(db.Unicode(10), nullable=False)
    first_category_id = db.Column(db.Integer, nullable=False)

    @staticmethod
    def generate_fake():
        categories = {u"椅凳类": [u'交椅', u'圈椅', u'太师椅', u'官帽椅', u'长凳', u'鼓凳', u'杌凳', u'宝座'], u"桌案类": [u'书桌', u'画案', u'条形桌案', u'方桌', u'八仙桌', u'炕桌', u'炕几'], u"床榻类": [u'拔步床', u'架子床', u'罗汉床', u'榻'], u"柜架类": [u'书柜', u'顶箱柜', u'方角柜', u'圆角柜', u'酒柜', u'书架', u'衣架', u'博古架'], u"其他类": [u'箱', u'屏风', u'挂件', u'手串', u'雕刻工艺品']}
        for category in categories:
            first_category = FirstCategory.query.filter_by(first_category=category).first()
            for second_category in categories[category]:
                db.session.add(SecondCategory(second_category=second_category, first_category_id=first_category.id))
            db.session.commit()


class ItemCategory(db.Model):
    __tablename__ = 'item_categories'
    id = db.Column(db.Integer, primary_key=True)
    item_id = db.Column(db.Integer, nullable=False)
    category_id = db.Column(db.Integer, nullable=False)


class FirstScene(db.Model):
    __tablename__ = 'first_scenes'
    id = db.Column(db.Integer, primary_key=True)
    first_scene = db.Column(db.Unicode(10), nullable=False)

    @staticmethod
    def generate_fake():
        scenes = [u'家庭', u'办公', u'工艺品', u'其他']
        for scene in scenes:
            db.session.add(FirstScene(first_scene=scene))
        db.session.commit()


class SecondScene(db.Model):
    __tablename__ = 'second_scenes'
    id = db.Column(db.Integer, primary_key=True)
    first_scene_id = db.Column(db.Integer, nullable=False)
    second_scene = db.Column(db.Unicode(10), nullable=False)

    @staticmethod
    def generate_fake():
        scenes = {u'家庭': [u'书房', u'客厅', u'卧室', u'厨卫', u'餐厅', u'儿童房'], u'办公': [u'酒店', u'工作室'],
                  u'工艺品': [u'工艺品'], u'其他': [u'其他']}
        for scene in scenes:
            first_scene = FirstScene.query.filter_by(first_scene=scene).first()
            for sec_scene in scenes[scene]:
                db.session.add(SecondScene(first_scene_id=first_scene.id, second_scene=sec_scene))
        db.session.commit()


class Material(db.Model):
    __tablename__ = 'materials'
    id = db.Column(db.Integer, primary_key=True)
    material = db.Column(db.Unicode(10), nullable=False)

    @staticmethod
    def generate_fake():
        materials = [u'紫檀木', u'花梨木', u'香枝木', u'黑酸枝木', u'红酸枝木', u'鸡翅木', u'乌木', u'条纹乌木']
        for material in materials:
            db.session.add(Material(material=material))
        db.session.commit()


class Privilege(BaseUser, db.Model):
    __tablename__ = 'privileges'
    # 用户名
    username = db.Column(db.String(12), nullable=False, unique=True)

    mobile = None

    id_prefix = privilege_id_prefix

    def __init__(self, password, email, username):
        self.username = username
        self.email = email
        self.password = password
        super(Privilege, self).__init__(password, '', email)

    @staticmethod
    def generate_fake():
        privilege = Privilege('14e1b600b1fd579f47433b88e8d85291', 'a@a.com', 'admin')
        db.session.add(privilege)
        db.session.commit()


class Province(db.Model):
    __tablename__ = 'provinces'
    id = db.Column(db.Integer, primary_key=True)
    cn_id = db.Column(db.Integer, nullable=False)
    province = db.Column(db.Unicode(15), nullable=False)

    def area_address(self):
        return self.province

    def grade(self):
        return self


class City(db.Model, Property):
    __tablename__ = 'cities'
    id = db.Column(db.Integer, primary_key=True)
    cn_id = db.Column(db.Integer, nullable=False)
    city = db.Column(db.Unicode(15), nullable=False)
    province_id = db.Column(db.Integer, nullable=False)

    _flush = {
        'province': lambda x: Province.query.get(x.province_id)
    }
    _province = None

    def area_address(self):
        if self.city in [u'北京市', u'上海市', u'天津市', u'重庆市']:
            return self.city
        return self.province.area_address() + self.city

    @property
    def province(self):
        return self.get_or_flush('province')

    def grade(self):
        return self.province.grade(), self


class District(db.Model, Property):
    __tablename__ = 'districts'
    id = db.Column(db.Integer, primary_key=True)
    cn_id = db.Column(db.Integer, nullable=False)
    district = db.Column(db.Unicode(15), nullable=False)
    city_id = db.Column(db.Integer, nullable=False)

    _flush = {
        'city': lambda x: City.query.get(x.city_id)
    }
    _city = None

    def area_address(self):
        return self.city.area_address() + self.district

    @property
    def city(self):
        return self.get_or_flush('city')

    def grade(self):
        province, city = self.city.grade()
        return province, city, self

    @staticmethod
    def generate_fake():
        directly_city = [u'北京市', u'天津市', u'上海市', u'重庆市']
        cn = [('110000', u'\u5317\u4eac\u5e02'), ('110100', u'\u5e02\u8f96\u533a'), ('110101', u'\u4e1c\u57ce\u533a'), ('110102', u'\u897f\u57ce\u533a'), ('110105', u'\u671d\u9633\u533a'), ('110106', u'\u4e30\u53f0\u533a'), ('110107', u'\u77f3\u666f\u5c71\u533a'), ('110108', u'\u6d77\u6dc0\u533a'), ('110109', u'\u95e8\u5934\u6c9f\u533a'), ('110111', u'\u623f\u5c71\u533a'), ('110112', u'\u901a\u5dde\u533a'), ('110113', u'\u987a\u4e49\u533a'), ('110114', u'\u660c\u5e73\u533a'), ('110115', u'\u5927\u5174\u533a'), ('110116', u'\u6000\u67d4\u533a'), ('110117', u'\u5e73\u8c37\u533a'), ('110200', u'\u53bf'), ('110228', u'\u5bc6\u4e91\u53bf'), ('110229', u'\u5ef6\u5e86\u53bf'), ('120000', u'\u5929\u6d25\u5e02'), ('120100', u'\u5e02\u8f96\u533a'), ('120101', u'\u548c\u5e73\u533a'), ('120102', u'\u6cb3\u4e1c\u533a'), ('120103', u'\u6cb3\u897f\u533a'), ('120104', u'\u5357\u5f00\u533a'), ('120105', u'\u6cb3\u5317\u533a'), ('120106', u'\u7ea2\u6865\u533a'), ('120110', u'\u4e1c\u4e3d\u533a'), ('120111', u'\u897f\u9752\u533a'), ('120112', u'\u6d25\u5357\u533a'), ('120113', u'\u5317\u8fb0\u533a'), ('120114', u'\u6b66\u6e05\u533a'), ('120115', u'\u5b9d\u577b\u533a'), ('120116', u'\u6ee8\u6d77\u65b0\u533a'), ('120200', u'\u53bf'), ('120221', u'\u5b81\u6cb3\u53bf'), ('120223', u'\u9759\u6d77\u53bf'), ('120225', u'\u84df\u53bf'), ('130000', u'\u6cb3\u5317\u7701'), ('130100', u'\u77f3\u5bb6\u5e84\u5e02'), ('130101', u'\u5e02\u8f96\u533a'), ('130102', u'\u957f\u5b89\u533a'), ('130103', u'\u6865\u4e1c\u533a'), ('130104', u'\u6865\u897f\u533a'), ('130105', u'\u65b0\u534e\u533a'), ('130107', u'\u4e95\u9649\u77ff\u533a'), ('130108', u'\u88d5\u534e\u533a'), ('130121', u'\u4e95\u9649\u53bf'), ('130123', u'\u6b63\u5b9a\u53bf'), ('130124', u'\u683e\u57ce\u53bf'), ('130125', u'\u884c\u5510\u53bf'), ('130126', u'\u7075\u5bff\u53bf'), ('130127', u'\u9ad8\u9091\u53bf'), ('130128', u'\u6df1\u6cfd\u53bf'), ('130129', u'\u8d5e\u7687\u53bf'), ('130130', u'\u65e0\u6781\u53bf'), ('130131', u'\u5e73\u5c71\u53bf'), ('130132', u'\u5143\u6c0f\u53bf'), ('130133', u'\u8d75\u53bf'), ('130181', u'\u8f9b\u96c6\u5e02'), ('130182', u'\u85c1\u57ce\u5e02'), ('130183', u'\u664b\u5dde\u5e02'), ('130184', u'\u65b0\u4e50\u5e02'), ('130185', u'\u9e7f\u6cc9\u5e02'), ('130200', u'\u5510\u5c71\u5e02'), ('130201', u'\u5e02\u8f96\u533a'), ('130202', u'\u8def\u5357\u533a'), ('130203', u'\u8def\u5317\u533a'), ('130204', u'\u53e4\u51b6\u533a'), ('130205', u'\u5f00\u5e73\u533a'), ('130207', u'\u4e30\u5357\u533a'), ('130208', u'\u4e30\u6da6\u533a'), ('130209', u'\u66f9\u5983\u7538\u533a'), ('130223', u'\u6ee6\u53bf'), ('130224', u'\u6ee6\u5357\u53bf'), ('130225', u'\u4e50\u4ead\u53bf'), ('130227', u'\u8fc1\u897f\u53bf'), ('130229', u'\u7389\u7530\u53bf'), ('130281', u'\u9075\u5316\u5e02'), ('130283', u'\u8fc1\u5b89\u5e02'), ('130300', u'\u79e6\u7687\u5c9b\u5e02'), ('130301', u'\u5e02\u8f96\u533a'), ('130302', u'\u6d77\u6e2f\u533a'), ('130303', u'\u5c71\u6d77\u5173\u533a'), ('130304', u'\u5317\u6234\u6cb3\u533a'), ('130321', u'\u9752\u9f99\u6ee1\u65cf\u81ea\u6cbb\u53bf'), ('130322', u'\u660c\u9ece\u53bf'), ('130323', u'\u629a\u5b81\u53bf'), ('130324', u'\u5362\u9f99\u53bf'), ('130400', u'\u90af\u90f8\u5e02'), ('130401', u'\u5e02\u8f96\u533a'), ('130402', u'\u90af\u5c71\u533a'), ('130403', u'\u4e1b\u53f0\u533a'), ('130404', u'\u590d\u5174\u533a'), ('130406', u'\u5cf0\u5cf0\u77ff\u533a'), ('130421', u'\u90af\u90f8\u53bf'), ('130423', u'\u4e34\u6f33\u53bf'), ('130424', u'\u6210\u5b89\u53bf'), ('130425', u'\u5927\u540d\u53bf'), ('130426', u'\u6d89\u53bf'), ('130427', u'\u78c1\u53bf'), ('130428', u'\u80a5\u4e61\u53bf'), ('130429', u'\u6c38\u5e74\u53bf'), ('130430', u'\u90b1\u53bf'), ('130431', u'\u9e21\u6cfd\u53bf'), ('130432', u'\u5e7f\u5e73\u53bf'), ('130433', u'\u9986\u9676\u53bf'), ('130434', u'\u9b4f\u53bf'), ('130435', u'\u66f2\u5468\u53bf'), ('130481', u'\u6b66\u5b89\u5e02'), ('130500', u'\u90a2\u53f0\u5e02'), ('130501', u'\u5e02\u8f96\u533a'), ('130502', u'\u6865\u4e1c\u533a'), ('130503', u'\u6865\u897f\u533a'), ('130521', u'\u90a2\u53f0\u53bf'), ('130522', u'\u4e34\u57ce\u53bf'), ('130523', u'\u5185\u4e18\u53bf'), ('130524', u'\u67cf\u4e61\u53bf'), ('130525', u'\u9686\u5c27\u53bf'), ('130526', u'\u4efb\u53bf'), ('130527', u'\u5357\u548c\u53bf'), ('130528', u'\u5b81\u664b\u53bf'), ('130529', u'\u5de8\u9e7f\u53bf'), ('130530', u'\u65b0\u6cb3\u53bf'), ('130531', u'\u5e7f\u5b97\u53bf'), ('130532', u'\u5e73\u4e61\u53bf'), ('130533', u'\u5a01\u53bf'), ('130534', u'\u6e05\u6cb3\u53bf'), ('130535', u'\u4e34\u897f\u53bf'), ('130581', u'\u5357\u5bab\u5e02'), ('130582', u'\u6c99\u6cb3\u5e02'), ('130600', u'\u4fdd\u5b9a\u5e02'), ('130601', u'\u5e02\u8f96\u533a'), ('130602', u'\u65b0\u5e02\u533a'), ('130603', u'\u5317\u5e02\u533a'), ('130604', u'\u5357\u5e02\u533a'), ('130621', u'\u6ee1\u57ce\u53bf'), ('130622', u'\u6e05\u82d1\u53bf'), ('130623', u'\u6d9e\u6c34\u53bf'), ('130624', u'\u961c\u5e73\u53bf'), ('130625', u'\u5f90\u6c34\u53bf'), ('130626', u'\u5b9a\u5174\u53bf'), ('130627', u'\u5510\u53bf'), ('130628', u'\u9ad8\u9633\u53bf'), ('130629', u'\u5bb9\u57ce\u53bf'), ('130630', u'\u6d9e\u6e90\u53bf'), ('130631', u'\u671b\u90fd\u53bf'), ('130632', u'\u5b89\u65b0\u53bf'), ('130633', u'\u6613\u53bf'), ('130634', u'\u66f2\u9633\u53bf'), ('130635', u'\u8821\u53bf'), ('130636', u'\u987a\u5e73\u53bf'), ('130637', u'\u535a\u91ce\u53bf'), ('130638', u'\u96c4\u53bf'), ('130681', u'\u6dbf\u5dde\u5e02'), ('130682', u'\u5b9a\u5dde\u5e02'), ('130683', u'\u5b89\u56fd\u5e02'), ('130684', u'\u9ad8\u7891\u5e97\u5e02'), ('130700', u'\u5f20\u5bb6\u53e3\u5e02'), ('130701', u'\u5e02\u8f96\u533a'), ('130702', u'\u6865\u4e1c\u533a'), ('130703', u'\u6865\u897f\u533a'), ('130705', u'\u5ba3\u5316\u533a'), ('130706', u'\u4e0b\u82b1\u56ed\u533a'), ('130721', u'\u5ba3\u5316\u53bf'), ('130722', u'\u5f20\u5317\u53bf'), ('130723', u'\u5eb7\u4fdd\u53bf'), ('130724', u'\u6cbd\u6e90\u53bf'), ('130725', u'\u5c1a\u4e49\u53bf'), ('130726', u'\u851a\u53bf'), ('130727', u'\u9633\u539f\u53bf'), ('130728', u'\u6000\u5b89\u53bf'), ('130729', u'\u4e07\u5168\u53bf'), ('130730', u'\u6000\u6765\u53bf'), ('130731', u'\u6dbf\u9e7f\u53bf'), ('130732', u'\u8d64\u57ce\u53bf'), ('130733', u'\u5d07\u793c\u53bf'), ('130800', u'\u627f\u5fb7\u5e02'), ('130801', u'\u5e02\u8f96\u533a'), ('130802', u'\u53cc\u6865\u533a'), ('130803', u'\u53cc\u6ee6\u533a'), ('130804', u'\u9e70\u624b\u8425\u5b50\u77ff\u533a'), ('130821', u'\u627f\u5fb7\u53bf'), ('130822', u'\u5174\u9686\u53bf'), ('130823', u'\u5e73\u6cc9\u53bf'), ('130824', u'\u6ee6\u5e73\u53bf'), ('130825', u'\u9686\u5316\u53bf'), ('130826', u'\u4e30\u5b81\u6ee1\u65cf\u81ea\u6cbb\u53bf'), ('130827', u'\u5bbd\u57ce\u6ee1\u65cf\u81ea\u6cbb\u53bf'), ('130828', u'\u56f4\u573a\u6ee1\u65cf\u8499\u53e4\u65cf\u81ea\u6cbb\u53bf'), ('130900', u'\u6ca7\u5dde\u5e02'), ('130901', u'\u5e02\u8f96\u533a'), ('130902', u'\u65b0\u534e\u533a'), ('130903', u'\u8fd0\u6cb3\u533a'), ('130921', u'\u6ca7\u53bf'), ('130922', u'\u9752\u53bf'), ('130923', u'\u4e1c\u5149\u53bf'), ('130924', u'\u6d77\u5174\u53bf'), ('130925', u'\u76d0\u5c71\u53bf'), ('130926', u'\u8083\u5b81\u53bf'), ('130927', u'\u5357\u76ae\u53bf'), ('130928', u'\u5434\u6865\u53bf'), ('130929', u'\u732e\u53bf'), ('130930', u'\u5b5f\u6751\u56de\u65cf\u81ea\u6cbb\u53bf'), ('130981', u'\u6cca\u5934\u5e02'), ('130982', u'\u4efb\u4e18\u5e02'), ('130983', u'\u9ec4\u9a85\u5e02'), ('130984', u'\u6cb3\u95f4\u5e02'), ('131000', u'\u5eca\u574a\u5e02'), ('131001', u'\u5e02\u8f96\u533a'), ('131002', u'\u5b89\u6b21\u533a'), ('131003', u'\u5e7f\u9633\u533a'), ('131022', u'\u56fa\u5b89\u53bf'), ('131023', u'\u6c38\u6e05\u53bf'), ('131024', u'\u9999\u6cb3\u53bf'), ('131025', u'\u5927\u57ce\u53bf'), ('131026', u'\u6587\u5b89\u53bf'), ('131028', u'\u5927\u5382\u56de\u65cf\u81ea\u6cbb\u53bf'), ('131081', u'\u9738\u5dde\u5e02'), ('131082', u'\u4e09\u6cb3\u5e02'), ('131100', u'\u8861\u6c34\u5e02'), ('131101', u'\u5e02\u8f96\u533a'), ('131102', u'\u6843\u57ce\u533a'), ('131121', u'\u67a3\u5f3a\u53bf'), ('131122', u'\u6b66\u9091\u53bf'), ('131123', u'\u6b66\u5f3a\u53bf'), ('131124', u'\u9976\u9633\u53bf'), ('131125', u'\u5b89\u5e73\u53bf'), ('131126', u'\u6545\u57ce\u53bf'), ('131127', u'\u666f\u53bf'), ('131128', u'\u961c\u57ce\u53bf'), ('131181', u'\u5180\u5dde\u5e02'), ('131182', u'\u6df1\u5dde\u5e02'), ('140000', u'\u5c71\u897f\u7701'), ('140100', u'\u592a\u539f\u5e02'), ('140101', u'\u5e02\u8f96\u533a'), ('140105', u'\u5c0f\u5e97\u533a'), ('140106', u'\u8fce\u6cfd\u533a'), ('140107', u'\u674f\u82b1\u5cad\u533a'), ('140108', u'\u5c16\u8349\u576a\u533a'), ('140109', u'\u4e07\u67cf\u6797\u533a'), ('140110', u'\u664b\u6e90\u533a'), ('140121', u'\u6e05\u5f90\u53bf'), ('140122', u'\u9633\u66f2\u53bf'), ('140123', u'\u5a04\u70e6\u53bf'), ('140181', u'\u53e4\u4ea4\u5e02'), ('140200', u'\u5927\u540c\u5e02'), ('140201', u'\u5e02\u8f96\u533a'), ('140202', u'\u57ce\u533a'), ('140203', u'\u77ff\u533a'), ('140211', u'\u5357\u90ca\u533a'), ('140212', u'\u65b0\u8363\u533a'), ('140221', u'\u9633\u9ad8\u53bf'), ('140222', u'\u5929\u9547\u53bf'), ('140223', u'\u5e7f\u7075\u53bf'), ('140224', u'\u7075\u4e18\u53bf'), ('140225', u'\u6d51\u6e90\u53bf'), ('140226', u'\u5de6\u4e91\u53bf'), ('140227', u'\u5927\u540c\u53bf'), ('140300', u'\u9633\u6cc9\u5e02'), ('140301', u'\u5e02\u8f96\u533a'), ('140302', u'\u57ce\u533a'), ('140303', u'\u77ff\u533a'), ('140311', u'\u90ca\u533a'), ('140321', u'\u5e73\u5b9a\u53bf'), ('140322', u'\u76c2\u53bf'), ('140400', u'\u957f\u6cbb\u5e02'), ('140401', u'\u5e02\u8f96\u533a'), ('140402', u'\u57ce\u533a'), ('140411', u'\u90ca\u533a'), ('140421', u'\u957f\u6cbb\u53bf'), ('140423', u'\u8944\u57a3\u53bf'), ('140424', u'\u5c6f\u7559\u53bf'), ('140425', u'\u5e73\u987a\u53bf'), ('140426', u'\u9ece\u57ce\u53bf'), ('140427', u'\u58f6\u5173\u53bf'), ('140428', u'\u957f\u5b50\u53bf'), ('140429', u'\u6b66\u4e61\u53bf'), ('140430', u'\u6c81\u53bf'), ('140431', u'\u6c81\u6e90\u53bf'), ('140481', u'\u6f5e\u57ce\u5e02'), ('140500', u'\u664b\u57ce\u5e02'), ('140501', u'\u5e02\u8f96\u533a'), ('140502', u'\u57ce\u533a'), ('140521', u'\u6c81\u6c34\u53bf'), ('140522', u'\u9633\u57ce\u53bf'), ('140524', u'\u9675\u5ddd\u53bf'), ('140525', u'\u6cfd\u5dde\u53bf'), ('140581', u'\u9ad8\u5e73\u5e02'), ('140600', u'\u6714\u5dde\u5e02'), ('140601', u'\u5e02\u8f96\u533a'), ('140602', u'\u6714\u57ce\u533a'), ('140603', u'\u5e73\u9c81\u533a'), ('140621', u'\u5c71\u9634\u53bf'), ('140622', u'\u5e94\u53bf'), ('140623', u'\u53f3\u7389\u53bf'), ('140624', u'\u6000\u4ec1\u53bf'), ('140700', u'\u664b\u4e2d\u5e02'), ('140701', u'\u5e02\u8f96\u533a'), ('140702', u'\u6986\u6b21\u533a'), ('140721', u'\u6986\u793e\u53bf'), ('140722', u'\u5de6\u6743\u53bf'), ('140723', u'\u548c\u987a\u53bf'), ('140724', u'\u6614\u9633\u53bf'), ('140725', u'\u5bff\u9633\u53bf'), ('140726', u'\u592a\u8c37\u53bf'), ('140727', u'\u7941\u53bf'), ('140728', u'\u5e73\u9065\u53bf'), ('140729', u'\u7075\u77f3\u53bf'), ('140781', u'\u4ecb\u4f11\u5e02'), ('140800', u'\u8fd0\u57ce\u5e02'), ('140801', u'\u5e02\u8f96\u533a'), ('140802', u'\u76d0\u6e56\u533a'), ('140821', u'\u4e34\u7317\u53bf'), ('140822', u'\u4e07\u8363\u53bf'), ('140823', u'\u95fb\u559c\u53bf'), ('140824', u'\u7a37\u5c71\u53bf'), ('140825', u'\u65b0\u7edb\u53bf'), ('140826', u'\u7edb\u53bf'), ('140827', u'\u57a3\u66f2\u53bf'), ('140828', u'\u590f\u53bf'), ('140829', u'\u5e73\u9646\u53bf'), ('140830', u'\u82ae\u57ce\u53bf'), ('140881', u'\u6c38\u6d4e\u5e02'), ('140882', u'\u6cb3\u6d25\u5e02'), ('140900', u'\u5ffb\u5dde\u5e02'), ('140901', u'\u5e02\u8f96\u533a'), ('140902', u'\u5ffb\u5e9c\u533a'), ('140921', u'\u5b9a\u8944\u53bf'), ('140922', u'\u4e94\u53f0\u53bf'), ('140923', u'\u4ee3\u53bf'), ('140924', u'\u7e41\u5cd9\u53bf'), ('140925', u'\u5b81\u6b66\u53bf'), ('140926', u'\u9759\u4e50\u53bf'), ('140927', u'\u795e\u6c60\u53bf'), ('140928', u'\u4e94\u5be8\u53bf'), ('140929', u'\u5ca2\u5c9a\u53bf'), ('140930', u'\u6cb3\u66f2\u53bf'), ('140931', u'\u4fdd\u5fb7\u53bf'), ('140932', u'\u504f\u5173\u53bf'), ('140981', u'\u539f\u5e73\u5e02'), ('141000', u'\u4e34\u6c7e\u5e02'), ('141001', u'\u5e02\u8f96\u533a'), ('141002', u'\u5c27\u90fd\u533a'), ('141021', u'\u66f2\u6c83\u53bf'), ('141022', u'\u7ffc\u57ce\u53bf'), ('141023', u'\u8944\u6c7e\u53bf'), ('141024', u'\u6d2a\u6d1e\u53bf'), ('141025', u'\u53e4\u53bf'), ('141026', u'\u5b89\u6cfd\u53bf'), ('141027', u'\u6d6e\u5c71\u53bf'), ('141028', u'\u5409\u53bf'), ('141029', u'\u4e61\u5b81\u53bf'), ('141030', u'\u5927\u5b81\u53bf'), ('141031', u'\u96b0\u53bf'), ('141032', u'\u6c38\u548c\u53bf'), ('141033', u'\u84b2\u53bf'), ('141034', u'\u6c7e\u897f\u53bf'), ('141081', u'\u4faf\u9a6c\u5e02'), ('141082', u'\u970d\u5dde\u5e02'), ('141100', u'\u5415\u6881\u5e02'), ('141101', u'\u5e02\u8f96\u533a'), ('141102', u'\u79bb\u77f3\u533a'), ('141121', u'\u6587\u6c34\u53bf'), ('141122', u'\u4ea4\u57ce\u53bf'), ('141123', u'\u5174\u53bf'), ('141124', u'\u4e34\u53bf'), ('141125', u'\u67f3\u6797\u53bf'), ('141126', u'\u77f3\u697c\u53bf'), ('141127', u'\u5c9a\u53bf'), ('141128', u'\u65b9\u5c71\u53bf'), ('141129', u'\u4e2d\u9633\u53bf'), ('141130', u'\u4ea4\u53e3\u53bf'), ('141181', u'\u5b5d\u4e49\u5e02'), ('141182', u'\u6c7e\u9633\u5e02'), ('150000', u'\u5185\u8499\u53e4\u81ea\u6cbb\u533a'), ('150100', u'\u547c\u548c\u6d69\u7279\u5e02'), ('150101', u'\u5e02\u8f96\u533a'), ('150102', u'\u65b0\u57ce\u533a'), ('150103', u'\u56de\u6c11\u533a'), ('150104', u'\u7389\u6cc9\u533a'), ('150105', u'\u8d5b\u7f55\u533a'), ('150121', u'\u571f\u9ed8\u7279\u5de6\u65d7'), ('150122', u'\u6258\u514b\u6258\u53bf'), ('150123', u'\u548c\u6797\u683c\u5c14\u53bf'), ('150124', u'\u6e05\u6c34\u6cb3\u53bf'), ('150125', u'\u6b66\u5ddd\u53bf'), ('150200', u'\u5305\u5934\u5e02'), ('150201', u'\u5e02\u8f96\u533a'), ('150202', u'\u4e1c\u6cb3\u533a'), ('150203', u'\u6606\u90fd\u4ed1\u533a'), ('150204', u'\u9752\u5c71\u533a'), ('150205', u'\u77f3\u62d0\u533a'), ('150206', u'\u767d\u4e91\u9102\u535a\u77ff\u533a'), ('150207', u'\u4e5d\u539f\u533a'), ('150221', u'\u571f\u9ed8\u7279\u53f3\u65d7'), ('150222', u'\u56fa\u9633\u53bf'), ('150223', u'\u8fbe\u5c14\u7f55\u8302\u660e\u5b89\u8054\u5408\u65d7'), ('150300', u'\u4e4c\u6d77\u5e02'), ('150301', u'\u5e02\u8f96\u533a'), ('150302', u'\u6d77\u52c3\u6e7e\u533a'), ('150303', u'\u6d77\u5357\u533a'), ('150304', u'\u4e4c\u8fbe\u533a'), ('150400', u'\u8d64\u5cf0\u5e02'), ('150401', u'\u5e02\u8f96\u533a'), ('150402', u'\u7ea2\u5c71\u533a'), ('150403', u'\u5143\u5b9d\u5c71\u533a'), ('150404', u'\u677e\u5c71\u533a'), ('150421', u'\u963f\u9c81\u79d1\u5c14\u6c81\u65d7'), ('150422', u'\u5df4\u6797\u5de6\u65d7'), ('150423', u'\u5df4\u6797\u53f3\u65d7'), ('150424', u'\u6797\u897f\u53bf'), ('150425', u'\u514b\u4ec0\u514b\u817e\u65d7'), ('150426', u'\u7fc1\u725b\u7279\u65d7'), ('150428', u'\u5580\u5587\u6c81\u65d7'), ('150429', u'\u5b81\u57ce\u53bf'), ('150430', u'\u6556\u6c49\u65d7'), ('150500', u'\u901a\u8fbd\u5e02'), ('150501', u'\u5e02\u8f96\u533a'), ('150502', u'\u79d1\u5c14\u6c81\u533a'), ('150521', u'\u79d1\u5c14\u6c81\u5de6\u7ffc\u4e2d\u65d7'), ('150522', u'\u79d1\u5c14\u6c81\u5de6\u7ffc\u540e\u65d7'), ('150523', u'\u5f00\u9c81\u53bf'), ('150524', u'\u5e93\u4f26\u65d7'), ('150525', u'\u5948\u66fc\u65d7'), ('150526', u'\u624e\u9c81\u7279\u65d7'), ('150581', u'\u970d\u6797\u90ed\u52d2\u5e02'), ('150600', u'\u9102\u5c14\u591a\u65af\u5e02'), ('150601', u'\u5e02\u8f96\u533a'), ('150602', u'\u4e1c\u80dc\u533a'), ('150621', u'\u8fbe\u62c9\u7279\u65d7'), ('150622', u'\u51c6\u683c\u5c14\u65d7'), ('150623', u'\u9102\u6258\u514b\u524d\u65d7'), ('150624', u'\u9102\u6258\u514b\u65d7'), ('150625', u'\u676d\u9526\u65d7'), ('150626', u'\u4e4c\u5ba1\u65d7'), ('150627', u'\u4f0a\u91d1\u970d\u6d1b\u65d7'), ('150700', u'\u547c\u4f26\u8d1d\u5c14\u5e02'), ('150701', u'\u5e02\u8f96\u533a'), ('150702', u'\u6d77\u62c9\u5c14\u533a'), ('150703', u'\u624e\u8d49\u8bfa\u5c14\u533a'), ('150721', u'\u963f\u8363\u65d7'), ('150722', u'\u83ab\u529b\u8fbe\u74e6\u8fbe\u65a1\u5c14\u65cf\u81ea\u6cbb\u65d7'), ('150723', u'\u9102\u4f26\u6625\u81ea\u6cbb\u65d7'), ('150724', u'\u9102\u6e29\u514b\u65cf\u81ea\u6cbb\u65d7'), ('150725', u'\u9648\u5df4\u5c14\u864e\u65d7'), ('150726', u'\u65b0\u5df4\u5c14\u864e\u5de6\u65d7'), ('150727', u'\u65b0\u5df4\u5c14\u864e\u53f3\u65d7'), ('150781', u'\u6ee1\u6d32\u91cc\u5e02'), ('150782', u'\u7259\u514b\u77f3\u5e02'), ('150783', u'\u624e\u5170\u5c6f\u5e02'), ('150784', u'\u989d\u5c14\u53e4\u7eb3\u5e02'), ('150785', u'\u6839\u6cb3\u5e02'), ('150800', u'\u5df4\u5f66\u6dd6\u5c14\u5e02'), ('150801', u'\u5e02\u8f96\u533a'), ('150802', u'\u4e34\u6cb3\u533a'), ('150821', u'\u4e94\u539f\u53bf'), ('150822', u'\u78f4\u53e3\u53bf'), ('150823', u'\u4e4c\u62c9\u7279\u524d\u65d7'), ('150824', u'\u4e4c\u62c9\u7279\u4e2d\u65d7'), ('150825', u'\u4e4c\u62c9\u7279\u540e\u65d7'), ('150826', u'\u676d\u9526\u540e\u65d7'), ('150900', u'\u4e4c\u5170\u5bdf\u5e03\u5e02'), ('150901', u'\u5e02\u8f96\u533a'), ('150902', u'\u96c6\u5b81\u533a'), ('150921', u'\u5353\u8d44\u53bf'), ('150922', u'\u5316\u5fb7\u53bf'), ('150923', u'\u5546\u90fd\u53bf'), ('150924', u'\u5174\u548c\u53bf'), ('150925', u'\u51c9\u57ce\u53bf'), ('150926', u'\u5bdf\u54c8\u5c14\u53f3\u7ffc\u524d\u65d7'), ('150927', u'\u5bdf\u54c8\u5c14\u53f3\u7ffc\u4e2d\u65d7'), ('150928', u'\u5bdf\u54c8\u5c14\u53f3\u7ffc\u540e\u65d7'), ('150929', u'\u56db\u5b50\u738b\u65d7'), ('150981', u'\u4e30\u9547\u5e02'), ('152200', u'\u5174\u5b89\u76df'), ('152201', u'\u4e4c\u5170\u6d69\u7279\u5e02'), ('152202', u'\u963f\u5c14\u5c71\u5e02'), ('152221', u'\u79d1\u5c14\u6c81\u53f3\u7ffc\u524d\u65d7'), ('152222', u'\u79d1\u5c14\u6c81\u53f3\u7ffc\u4e2d\u65d7'), ('152223', u'\u624e\u8d49\u7279\u65d7'), ('152224', u'\u7a81\u6cc9\u53bf'), ('152500', u'\u9521\u6797\u90ed\u52d2\u76df'), ('152501', u'\u4e8c\u8fde\u6d69\u7279\u5e02'), ('152502', u'\u9521\u6797\u6d69\u7279\u5e02'), ('152522', u'\u963f\u5df4\u560e\u65d7'), ('152523', u'\u82cf\u5c3c\u7279\u5de6\u65d7'), ('152524', u'\u82cf\u5c3c\u7279\u53f3\u65d7'), ('152525', u'\u4e1c\u4e4c\u73e0\u7a46\u6c81\u65d7'), ('152526', u'\u897f\u4e4c\u73e0\u7a46\u6c81\u65d7'), ('152527', u'\u592a\u4ec6\u5bfa\u65d7'), ('152528', u'\u9576\u9ec4\u65d7'), ('152529', u'\u6b63\u9576\u767d\u65d7'), ('152530', u'\u6b63\u84dd\u65d7'), ('152531', u'\u591a\u4f26\u53bf'), ('152900', u'\u963f\u62c9\u5584\u76df'), ('152921', u'\u963f\u62c9\u5584\u5de6\u65d7'), ('152922', u'\u963f\u62c9\u5584\u53f3\u65d7'), ('152923', u'\u989d\u6d4e\u7eb3\u65d7'), ('210000', u'\u8fbd\u5b81\u7701'), ('210100', u'\u6c88\u9633\u5e02'), ('210101', u'\u5e02\u8f96\u533a'), ('210102', u'\u548c\u5e73\u533a'), ('210103', u'\u6c88\u6cb3\u533a'), ('210104', u'\u5927\u4e1c\u533a'), ('210105', u'\u7687\u59d1\u533a'), ('210106', u'\u94c1\u897f\u533a'), ('210111', u'\u82cf\u5bb6\u5c6f\u533a'), ('210112', u'\u4e1c\u9675\u533a'), ('210113', u'\u6c88\u5317\u65b0\u533a'), ('210114', u'\u4e8e\u6d2a\u533a'), ('210122', u'\u8fbd\u4e2d\u53bf'), ('210123', u'\u5eb7\u5e73\u53bf'), ('210124', u'\u6cd5\u5e93\u53bf'), ('210181', u'\u65b0\u6c11\u5e02'), ('210200', u'\u5927\u8fde\u5e02'), ('210201', u'\u5e02\u8f96\u533a'), ('210202', u'\u4e2d\u5c71\u533a'), ('210203', u'\u897f\u5c97\u533a'), ('210204', u'\u6c99\u6cb3\u53e3\u533a'), ('210211', u'\u7518\u4e95\u5b50\u533a'), ('210212', u'\u65c5\u987a\u53e3\u533a'), ('210213', u'\u91d1\u5dde\u533a'), ('210224', u'\u957f\u6d77\u53bf'), ('210281', u'\u74e6\u623f\u5e97\u5e02'), ('210282', u'\u666e\u5170\u5e97\u5e02'), ('210283', u'\u5e84\u6cb3\u5e02'), ('210300', u'\u978d\u5c71\u5e02'), ('210301', u'\u5e02\u8f96\u533a'), ('210302', u'\u94c1\u4e1c\u533a'), ('210303', u'\u94c1\u897f\u533a'), ('210304', u'\u7acb\u5c71\u533a'), ('210311', u'\u5343\u5c71\u533a'), ('210321', u'\u53f0\u5b89\u53bf'), ('210323', u'\u5cab\u5ca9\u6ee1\u65cf\u81ea\u6cbb\u53bf'), ('210381', u'\u6d77\u57ce\u5e02'), ('210400', u'\u629a\u987a\u5e02'), ('210401', u'\u5e02\u8f96\u533a'), ('210402', u'\u65b0\u629a\u533a'), ('210403', u'\u4e1c\u6d32\u533a'), ('210404', u'\u671b\u82b1\u533a'), ('210411', u'\u987a\u57ce\u533a'), ('210421', u'\u629a\u987a\u53bf'), ('210422', u'\u65b0\u5bbe\u6ee1\u65cf\u81ea\u6cbb\u53bf'), ('210423', u'\u6e05\u539f\u6ee1\u65cf\u81ea\u6cbb\u53bf'), ('210500', u'\u672c\u6eaa\u5e02'), ('210501', u'\u5e02\u8f96\u533a'), ('210502', u'\u5e73\u5c71\u533a'), ('210503', u'\u6eaa\u6e56\u533a'), ('210504', u'\u660e\u5c71\u533a'), ('210505', u'\u5357\u82ac\u533a'), ('210521', u'\u672c\u6eaa\u6ee1\u65cf\u81ea\u6cbb\u53bf'), ('210522', u'\u6853\u4ec1\u6ee1\u65cf\u81ea\u6cbb\u53bf'), ('210600', u'\u4e39\u4e1c\u5e02'), ('210601', u'\u5e02\u8f96\u533a'), ('210602', u'\u5143\u5b9d\u533a'), ('210603', u'\u632f\u5174\u533a'), ('210604', u'\u632f\u5b89\u533a'), ('210624', u'\u5bbd\u7538\u6ee1\u65cf\u81ea\u6cbb\u53bf'), ('210681', u'\u4e1c\u6e2f\u5e02'), ('210682', u'\u51e4\u57ce\u5e02'), ('210700', u'\u9526\u5dde\u5e02'), ('210701', u'\u5e02\u8f96\u533a'), ('210702', u'\u53e4\u5854\u533a'), ('210703', u'\u51cc\u6cb3\u533a'), ('210711', u'\u592a\u548c\u533a'), ('210726', u'\u9ed1\u5c71\u53bf'), ('210727', u'\u4e49\u53bf'), ('210781', u'\u51cc\u6d77\u5e02'), ('210782', u'\u5317\u9547\u5e02'), ('210800', u'\u8425\u53e3\u5e02'), ('210801', u'\u5e02\u8f96\u533a'), ('210802', u'\u7ad9\u524d\u533a'), ('210803', u'\u897f\u5e02\u533a'), ('210804', u'\u9c85\u9c7c\u5708\u533a'), ('210811', u'\u8001\u8fb9\u533a'), ('210881', u'\u76d6\u5dde\u5e02'), ('210882', u'\u5927\u77f3\u6865\u5e02'), ('210900', u'\u961c\u65b0\u5e02'), ('210901', u'\u5e02\u8f96\u533a'), ('210902', u'\u6d77\u5dde\u533a'), ('210903', u'\u65b0\u90b1\u533a'), ('210904', u'\u592a\u5e73\u533a'), ('210905', u'\u6e05\u6cb3\u95e8\u533a'), ('210911', u'\u7ec6\u6cb3\u533a'), ('210921', u'\u961c\u65b0\u8499\u53e4\u65cf\u81ea\u6cbb\u53bf'), ('210922', u'\u5f70\u6b66\u53bf'), ('211000', u'\u8fbd\u9633\u5e02'), ('211001', u'\u5e02\u8f96\u533a'), ('211002', u'\u767d\u5854\u533a'), ('211003', u'\u6587\u5723\u533a'), ('211004', u'\u5b8f\u4f1f\u533a'), ('211005', u'\u5f13\u957f\u5cad\u533a'), ('211011', u'\u592a\u5b50\u6cb3\u533a'), ('211021', u'\u8fbd\u9633\u53bf'), ('211081', u'\u706f\u5854\u5e02'), ('211100', u'\u76d8\u9526\u5e02'), ('211101', u'\u5e02\u8f96\u533a'), ('211102', u'\u53cc\u53f0\u5b50\u533a'), ('211103', u'\u5174\u9686\u53f0\u533a'), ('211121', u'\u5927\u6d3c\u53bf'), ('211122', u'\u76d8\u5c71\u53bf'), ('211200', u'\u94c1\u5cad\u5e02'), ('211201', u'\u5e02\u8f96\u533a'), ('211202', u'\u94f6\u5dde\u533a'), ('211204', u'\u6e05\u6cb3\u533a'), ('211221', u'\u94c1\u5cad\u53bf'), ('211223', u'\u897f\u4e30\u53bf'), ('211224', u'\u660c\u56fe\u53bf'), ('211281', u'\u8c03\u5175\u5c71\u5e02'), ('211282', u'\u5f00\u539f\u5e02'), ('211300', u'\u671d\u9633\u5e02'), ('211301', u'\u5e02\u8f96\u533a'), ('211302', u'\u53cc\u5854\u533a'), ('211303', u'\u9f99\u57ce\u533a'), ('211321', u'\u671d\u9633\u53bf'), ('211322', u'\u5efa\u5e73\u53bf'), ('211324', u'\u5580\u5587\u6c81\u5de6\u7ffc\u8499\u53e4\u65cf\u81ea\u6cbb\u53bf'), ('211381', u'\u5317\u7968\u5e02'), ('211382', u'\u51cc\u6e90\u5e02'), ('211400', u'\u846b\u82a6\u5c9b\u5e02'), ('211401', u'\u5e02\u8f96\u533a'), ('211402', u'\u8fde\u5c71\u533a'), ('211403', u'\u9f99\u6e2f\u533a'), ('211404', u'\u5357\u7968\u533a'), ('211421', u'\u7ee5\u4e2d\u53bf'), ('211422', u'\u5efa\u660c\u53bf'), ('211481', u'\u5174\u57ce\u5e02'), ('220000', u'\u5409\u6797\u7701'), ('220100', u'\u957f\u6625\u5e02'), ('220101', u'\u5e02\u8f96\u533a'), ('220102', u'\u5357\u5173\u533a'), ('220103', u'\u5bbd\u57ce\u533a'), ('220104', u'\u671d\u9633\u533a'), ('220105', u'\u4e8c\u9053\u533a'), ('220106', u'\u7eff\u56ed\u533a'), ('220112', u'\u53cc\u9633\u533a'), ('220122', u'\u519c\u5b89\u53bf'), ('220181', u'\u4e5d\u53f0\u5e02'), ('220182', u'\u6986\u6811\u5e02'), ('220183', u'\u5fb7\u60e0\u5e02'), ('220200', u'\u5409\u6797\u5e02'), ('220201', u'\u5e02\u8f96\u533a'), ('220202', u'\u660c\u9091\u533a'), ('220203', u'\u9f99\u6f6d\u533a'), ('220204', u'\u8239\u8425\u533a'), ('220211', u'\u4e30\u6ee1\u533a'), ('220221', u'\u6c38\u5409\u53bf'), ('220281', u'\u86df\u6cb3\u5e02'), ('220282', u'\u6866\u7538\u5e02'), ('220283', u'\u8212\u5170\u5e02'), ('220284', u'\u78d0\u77f3\u5e02'), ('220300', u'\u56db\u5e73\u5e02'), ('220301', u'\u5e02\u8f96\u533a'), ('220302', u'\u94c1\u897f\u533a'), ('220303', u'\u94c1\u4e1c\u533a'), ('220322', u'\u68a8\u6811\u53bf'), ('220323', u'\u4f0a\u901a\u6ee1\u65cf\u81ea\u6cbb\u53bf'), ('220381', u'\u516c\u4e3b\u5cad\u5e02'), ('220382', u'\u53cc\u8fbd\u5e02'), ('220400', u'\u8fbd\u6e90\u5e02'), ('220401', u'\u5e02\u8f96\u533a'), ('220402', u'\u9f99\u5c71\u533a'), ('220403', u'\u897f\u5b89\u533a'), ('220421', u'\u4e1c\u4e30\u53bf'), ('220422', u'\u4e1c\u8fbd\u53bf'), ('220500', u'\u901a\u5316\u5e02'), ('220501', u'\u5e02\u8f96\u533a'), ('220502', u'\u4e1c\u660c\u533a'), ('220503', u'\u4e8c\u9053\u6c5f\u533a'), ('220521', u'\u901a\u5316\u53bf'), ('220523', u'\u8f89\u5357\u53bf'), ('220524', u'\u67f3\u6cb3\u53bf'), ('220581', u'\u6885\u6cb3\u53e3\u5e02'), ('220582', u'\u96c6\u5b89\u5e02'), ('220600', u'\u767d\u5c71\u5e02'), ('220601', u'\u5e02\u8f96\u533a'), ('220602', u'\u6d51\u6c5f\u533a'), ('220605', u'\u6c5f\u6e90\u533a'), ('220621', u'\u629a\u677e\u53bf'), ('220622', u'\u9756\u5b87\u53bf'), ('220623', u'\u957f\u767d\u671d\u9c9c\u65cf\u81ea\u6cbb\u53bf'), ('220681', u'\u4e34\u6c5f\u5e02'), ('220700', u'\u677e\u539f\u5e02'), ('220701', u'\u5e02\u8f96\u533a'), ('220702', u'\u5b81\u6c5f\u533a'), ('220721', u'\u524d\u90ed\u5c14\u7f57\u65af\u8499\u53e4\u65cf\u81ea\u6cbb\u53bf'), ('220722', u'\u957f\u5cad\u53bf'), ('220723', u'\u4e7e\u5b89\u53bf'), ('220781', u'\u6276\u4f59\u5e02'), ('220800', u'\u767d\u57ce\u5e02'), ('220801', u'\u5e02\u8f96\u533a'), ('220802', u'\u6d2e\u5317\u533a'), ('220821', u'\u9547\u8d49\u53bf'), ('220822', u'\u901a\u6986\u53bf'), ('220881', u'\u6d2e\u5357\u5e02'), ('220882', u'\u5927\u5b89\u5e02'), ('222400', u'\u5ef6\u8fb9\u671d\u9c9c\u65cf\u81ea\u6cbb\u5dde'), ('222401', u'\u5ef6\u5409\u5e02'), ('222402', u'\u56fe\u4eec\u5e02'), ('222403', u'\u6566\u5316\u5e02'), ('222404', u'\u73f2\u6625\u5e02'), ('222405', u'\u9f99\u4e95\u5e02'), ('222406', u'\u548c\u9f99\u5e02'), ('222424', u'\u6c6a\u6e05\u53bf'), ('222426', u'\u5b89\u56fe\u53bf'), ('230000', u'\u9ed1\u9f99\u6c5f\u7701'), ('230100', u'\u54c8\u5c14\u6ee8\u5e02'), ('230101', u'\u5e02\u8f96\u533a'), ('230102', u'\u9053\u91cc\u533a'), ('230103', u'\u5357\u5c97\u533a'), ('230104', u'\u9053\u5916\u533a'), ('230108', u'\u5e73\u623f\u533a'), ('230109', u'\u677e\u5317\u533a'), ('230110', u'\u9999\u574a\u533a'), ('230111', u'\u547c\u5170\u533a'), ('230112', u'\u963f\u57ce\u533a'), ('230123', u'\u4f9d\u5170\u53bf'), ('230124', u'\u65b9\u6b63\u53bf'), ('230125', u'\u5bbe\u53bf'), ('230126', u'\u5df4\u5f66\u53bf'), ('230127', u'\u6728\u5170\u53bf'), ('230128', u'\u901a\u6cb3\u53bf'), ('230129', u'\u5ef6\u5bff\u53bf'), ('230182', u'\u53cc\u57ce\u5e02'), ('230183', u'\u5c1a\u5fd7\u5e02'), ('230184', u'\u4e94\u5e38\u5e02'), ('230200', u'\u9f50\u9f50\u54c8\u5c14\u5e02'), ('230201', u'\u5e02\u8f96\u533a'), ('230202', u'\u9f99\u6c99\u533a'), ('230203', u'\u5efa\u534e\u533a'), ('230204', u'\u94c1\u950b\u533a'), ('230205', u'\u6602\u6602\u6eaa\u533a'), ('230206', u'\u5bcc\u62c9\u5c14\u57fa\u533a'), ('230207', u'\u78be\u5b50\u5c71\u533a'), ('230208', u'\u6885\u91cc\u65af\u8fbe\u65a1\u5c14\u65cf\u533a'), ('230221', u'\u9f99\u6c5f\u53bf'), ('230223', u'\u4f9d\u5b89\u53bf'), ('230224', u'\u6cf0\u6765\u53bf'), ('230225', u'\u7518\u5357\u53bf'), ('230227', u'\u5bcc\u88d5\u53bf'), ('230229', u'\u514b\u5c71\u53bf'), ('230230', u'\u514b\u4e1c\u53bf'), ('230231', u'\u62dc\u6cc9\u53bf'), ('230281', u'\u8bb7\u6cb3\u5e02'), ('230300', u'\u9e21\u897f\u5e02'), ('230301', u'\u5e02\u8f96\u533a'), ('230302', u'\u9e21\u51a0\u533a'), ('230303', u'\u6052\u5c71\u533a'), ('230304', u'\u6ef4\u9053\u533a'), ('230305', u'\u68a8\u6811\u533a'), ('230306', u'\u57ce\u5b50\u6cb3\u533a'), ('230307', u'\u9ebb\u5c71\u533a'), ('230321', u'\u9e21\u4e1c\u53bf'), ('230381', u'\u864e\u6797\u5e02'), ('230382', u'\u5bc6\u5c71\u5e02'), ('230400', u'\u9e64\u5c97\u5e02'), ('230401', u'\u5e02\u8f96\u533a'), ('230402', u'\u5411\u9633\u533a'), ('230403', u'\u5de5\u519c\u533a'), ('230404', u'\u5357\u5c71\u533a'), ('230405', u'\u5174\u5b89\u533a'), ('230406', u'\u4e1c\u5c71\u533a'), ('230407', u'\u5174\u5c71\u533a'), ('230421', u'\u841d\u5317\u53bf'), ('230422', u'\u7ee5\u6ee8\u53bf'), ('230500', u'\u53cc\u9e2d\u5c71\u5e02'), ('230501', u'\u5e02\u8f96\u533a'), ('230502', u'\u5c16\u5c71\u533a'), ('230503', u'\u5cad\u4e1c\u533a'), ('230505', u'\u56db\u65b9\u53f0\u533a'), ('230506', u'\u5b9d\u5c71\u533a'), ('230521', u'\u96c6\u8d24\u53bf'), ('230522', u'\u53cb\u8c0a\u53bf'), ('230523', u'\u5b9d\u6e05\u53bf'), ('230524', u'\u9976\u6cb3\u53bf'), ('230600', u'\u5927\u5e86\u5e02'), ('230601', u'\u5e02\u8f96\u533a'), ('230602', u'\u8428\u5c14\u56fe\u533a'), ('230603', u'\u9f99\u51e4\u533a'), ('230604', u'\u8ba9\u80e1\u8def\u533a'), ('230605', u'\u7ea2\u5c97\u533a'), ('230606', u'\u5927\u540c\u533a'), ('230621', u'\u8087\u5dde\u53bf'), ('230622', u'\u8087\u6e90\u53bf'), ('230623', u'\u6797\u7538\u53bf'), ('230624', u'\u675c\u5c14\u4f2f\u7279\u8499\u53e4\u65cf\u81ea\u6cbb\u53bf'), ('230700', u'\u4f0a\u6625\u5e02'), ('230701', u'\u5e02\u8f96\u533a'), ('230702', u'\u4f0a\u6625\u533a'), ('230703', u'\u5357\u5c94\u533a'), ('230704', u'\u53cb\u597d\u533a'), ('230705', u'\u897f\u6797\u533a'), ('230706', u'\u7fe0\u5ce6\u533a'), ('230707', u'\u65b0\u9752\u533a'), ('230708', u'\u7f8e\u6eaa\u533a'), ('230709', u'\u91d1\u5c71\u5c6f\u533a'), ('230710', u'\u4e94\u8425\u533a'), ('230711', u'\u4e4c\u9a6c\u6cb3\u533a'), ('230712', u'\u6c64\u65fa\u6cb3\u533a'), ('230713', u'\u5e26\u5cad\u533a'), ('230714', u'\u4e4c\u4f0a\u5cad\u533a'), ('230715', u'\u7ea2\u661f\u533a'), ('230716', u'\u4e0a\u7518\u5cad\u533a'), ('230722', u'\u5609\u836b\u53bf'), ('230781', u'\u94c1\u529b\u5e02'), ('230800', u'\u4f73\u6728\u65af\u5e02'), ('230801', u'\u5e02\u8f96\u533a'), ('230803', u'\u5411\u9633\u533a'), ('230804', u'\u524d\u8fdb\u533a'), ('230805', u'\u4e1c\u98ce\u533a'), ('230811', u'\u90ca\u533a'), ('230822', u'\u6866\u5357\u53bf'), ('230826', u'\u6866\u5ddd\u53bf'), ('230828', u'\u6c64\u539f\u53bf'), ('230833', u'\u629a\u8fdc\u53bf'), ('230881', u'\u540c\u6c5f\u5e02'), ('230882', u'\u5bcc\u9526\u5e02'), ('230900', u'\u4e03\u53f0\u6cb3\u5e02'), ('230901', u'\u5e02\u8f96\u533a'), ('230902', u'\u65b0\u5174\u533a'), ('230903', u'\u6843\u5c71\u533a'), ('230904', u'\u8304\u5b50\u6cb3\u533a'), ('230921', u'\u52c3\u5229\u53bf'), ('231000', u'\u7261\u4e39\u6c5f\u5e02'), ('231001', u'\u5e02\u8f96\u533a'), ('231002', u'\u4e1c\u5b89\u533a'), ('231003', u'\u9633\u660e\u533a'), ('231004', u'\u7231\u6c11\u533a'), ('231005', u'\u897f\u5b89\u533a'), ('231024', u'\u4e1c\u5b81\u53bf'), ('231025', u'\u6797\u53e3\u53bf'), ('231081', u'\u7ee5\u82ac\u6cb3\u5e02'), ('231083', u'\u6d77\u6797\u5e02'), ('231084', u'\u5b81\u5b89\u5e02'), ('231085', u'\u7a46\u68f1\u5e02'), ('231100', u'\u9ed1\u6cb3\u5e02'), ('231101', u'\u5e02\u8f96\u533a'), ('231102', u'\u7231\u8f89\u533a'), ('231121', u'\u5ae9\u6c5f\u53bf'), ('231123', u'\u900a\u514b\u53bf'), ('231124', u'\u5b59\u5434\u53bf'), ('231181', u'\u5317\u5b89\u5e02'), ('231182', u'\u4e94\u5927\u8fde\u6c60\u5e02'), ('231200', u'\u7ee5\u5316\u5e02'), ('231201', u'\u5e02\u8f96\u533a'), ('231202', u'\u5317\u6797\u533a'), ('231221', u'\u671b\u594e\u53bf'), ('231222', u'\u5170\u897f\u53bf'), ('231223', u'\u9752\u5188\u53bf'), ('231224', u'\u5e86\u5b89\u53bf'), ('231225', u'\u660e\u6c34\u53bf'), ('231226', u'\u7ee5\u68f1\u53bf'), ('231281', u'\u5b89\u8fbe\u5e02'), ('231282', u'\u8087\u4e1c\u5e02'), ('231283', u'\u6d77\u4f26\u5e02'), ('232700', u'\u5927\u5174\u5b89\u5cad\u5730\u533a'), ('232721', u'\u547c\u739b\u53bf'), ('232722', u'\u5854\u6cb3\u53bf'), ('232723', u'\u6f20\u6cb3\u53bf'), ('310000', u'\u4e0a\u6d77\u5e02'), ('310100', u'\u5e02\u8f96\u533a'), ('310101', u'\u9ec4\u6d66\u533a'), ('310104', u'\u5f90\u6c47\u533a'), ('310105', u'\u957f\u5b81\u533a'), ('310106', u'\u9759\u5b89\u533a'), ('310107', u'\u666e\u9640\u533a'), ('310108', u'\u95f8\u5317\u533a'), ('310109', u'\u8679\u53e3\u533a'), ('310110', u'\u6768\u6d66\u533a'), ('310112', u'\u95f5\u884c\u533a'), ('310113', u'\u5b9d\u5c71\u533a'), ('310114', u'\u5609\u5b9a\u533a'), ('310115', u'\u6d66\u4e1c\u65b0\u533a'), ('310116', u'\u91d1\u5c71\u533a'), ('310117', u'\u677e\u6c5f\u533a'), ('310118', u'\u9752\u6d66\u533a'), ('310120', u'\u5949\u8d24\u533a'), ('310200', u'\u53bf'), ('310230', u'\u5d07\u660e\u53bf'), ('320000', u'\u6c5f\u82cf\u7701'), ('320100', u'\u5357\u4eac\u5e02'), ('320101', u'\u5e02\u8f96\u533a'), ('320102', u'\u7384\u6b66\u533a'), ('320104', u'\u79e6\u6dee\u533a'), ('320105', u'\u5efa\u90ba\u533a'), ('320106', u'\u9f13\u697c\u533a'), ('320111', u'\u6d66\u53e3\u533a'), ('320113', u'\u6816\u971e\u533a'), ('320114', u'\u96e8\u82b1\u53f0\u533a'), ('320115', u'\u6c5f\u5b81\u533a'), ('320116', u'\u516d\u5408\u533a'), ('320117', u'\u6ea7\u6c34\u533a'), ('320118', u'\u9ad8\u6df3\u533a'), ('320200', u'\u65e0\u9521\u5e02'), ('320201', u'\u5e02\u8f96\u533a'), ('320202', u'\u5d07\u5b89\u533a'), ('320203', u'\u5357\u957f\u533a'), ('320204', u'\u5317\u5858\u533a'), ('320205', u'\u9521\u5c71\u533a'), ('320206', u'\u60e0\u5c71\u533a'), ('320211', u'\u6ee8\u6e56\u533a'), ('320281', u'\u6c5f\u9634\u5e02'), ('320282', u'\u5b9c\u5174\u5e02'), ('320300', u'\u5f90\u5dde\u5e02'), ('320301', u'\u5e02\u8f96\u533a'), ('320302', u'\u9f13\u697c\u533a'), ('320303', u'\u4e91\u9f99\u533a'), ('320305', u'\u8d3e\u6c6a\u533a'), ('320311', u'\u6cc9\u5c71\u533a'), ('320312', u'\u94dc\u5c71\u533a'), ('320321', u'\u4e30\u53bf'), ('320322', u'\u6c9b\u53bf'), ('320324', u'\u7762\u5b81\u53bf'), ('320381', u'\u65b0\u6c82\u5e02'), ('320382', u'\u90b3\u5dde\u5e02'), ('320400', u'\u5e38\u5dde\u5e02'), ('320401', u'\u5e02\u8f96\u533a'), ('320402', u'\u5929\u5b81\u533a'), ('320404', u'\u949f\u697c\u533a'), ('320405', u'\u621a\u5885\u5830\u533a'), ('320411', u'\u65b0\u5317\u533a'), ('320412', u'\u6b66\u8fdb\u533a'), ('320481', u'\u6ea7\u9633\u5e02'), ('320482', u'\u91d1\u575b\u5e02'), ('320500', u'\u82cf\u5dde\u5e02'), ('320501', u'\u5e02\u8f96\u533a'), ('320505', u'\u864e\u4e18\u533a'), ('320506', u'\u5434\u4e2d\u533a'), ('320507', u'\u76f8\u57ce\u533a'), ('320508', u'\u59d1\u82cf\u533a'), ('320509', u'\u5434\u6c5f\u533a'), ('320581', u'\u5e38\u719f\u5e02'), ('320582', u'\u5f20\u5bb6\u6e2f\u5e02'), ('320583', u'\u6606\u5c71\u5e02'), ('320585', u'\u592a\u4ed3\u5e02'), ('320600', u'\u5357\u901a\u5e02'), ('320601', u'\u5e02\u8f96\u533a'), ('320602', u'\u5d07\u5ddd\u533a'), ('320611', u'\u6e2f\u95f8\u533a'), ('320612', u'\u901a\u5dde\u533a'), ('320621', u'\u6d77\u5b89\u53bf'), ('320623', u'\u5982\u4e1c\u53bf'), ('320681', u'\u542f\u4e1c\u5e02'), ('320682', u'\u5982\u768b\u5e02'), ('320684', u'\u6d77\u95e8\u5e02'), ('320700', u'\u8fde\u4e91\u6e2f\u5e02'), ('320701', u'\u5e02\u8f96\u533a'), ('320703', u'\u8fde\u4e91\u533a'), ('320705', u'\u65b0\u6d66\u533a'), ('320706', u'\u6d77\u5dde\u533a'), ('320721', u'\u8d63\u6986\u53bf'), ('320722', u'\u4e1c\u6d77\u53bf'), ('320723', u'\u704c\u4e91\u53bf'), ('320724', u'\u704c\u5357\u53bf'), ('320800', u'\u6dee\u5b89\u5e02'), ('320801', u'\u5e02\u8f96\u533a'), ('320802', u'\u6e05\u6cb3\u533a'), ('320803', u'\u6dee\u5b89\u533a'), ('320804', u'\u6dee\u9634\u533a'), ('320811', u'\u6e05\u6d66\u533a'), ('320826', u'\u6d9f\u6c34\u53bf'), ('320829', u'\u6d2a\u6cfd\u53bf'), ('320830', u'\u76f1\u7719\u53bf'), ('320831', u'\u91d1\u6e56\u53bf'), ('320900', u'\u76d0\u57ce\u5e02'), ('320901', u'\u5e02\u8f96\u533a'), ('320902', u'\u4ead\u6e56\u533a'), ('320903', u'\u76d0\u90fd\u533a'), ('320921', u'\u54cd\u6c34\u53bf'), ('320922', u'\u6ee8\u6d77\u53bf'), ('320923', u'\u961c\u5b81\u53bf'), ('320924', u'\u5c04\u9633\u53bf'), ('320925', u'\u5efa\u6e56\u53bf'), ('320981', u'\u4e1c\u53f0\u5e02'), ('320982', u'\u5927\u4e30\u5e02'), ('321000', u'\u626c\u5dde\u5e02'), ('321001', u'\u5e02\u8f96\u533a'), ('321002', u'\u5e7f\u9675\u533a'), ('321003', u'\u9097\u6c5f\u533a'), ('321012', u'\u6c5f\u90fd\u533a'), ('321023', u'\u5b9d\u5e94\u53bf'), ('321081', u'\u4eea\u5f81\u5e02'), ('321084', u'\u9ad8\u90ae\u5e02'), ('321100', u'\u9547\u6c5f\u5e02'), ('321101', u'\u5e02\u8f96\u533a'), ('321102', u'\u4eac\u53e3\u533a'), ('321111', u'\u6da6\u5dde\u533a'), ('321112', u'\u4e39\u5f92\u533a'), ('321181', u'\u4e39\u9633\u5e02'), ('321182', u'\u626c\u4e2d\u5e02'), ('321183', u'\u53e5\u5bb9\u5e02'), ('321200', u'\u6cf0\u5dde\u5e02'), ('321201', u'\u5e02\u8f96\u533a'), ('321202', u'\u6d77\u9675\u533a'), ('321203', u'\u9ad8\u6e2f\u533a'), ('321204', u'\u59dc\u5830\u533a'), ('321281', u'\u5174\u5316\u5e02'), ('321282', u'\u9756\u6c5f\u5e02'), ('321283', u'\u6cf0\u5174\u5e02'), ('321300', u'\u5bbf\u8fc1\u5e02'), ('321301', u'\u5e02\u8f96\u533a'), ('321302', u'\u5bbf\u57ce\u533a'), ('321311', u'\u5bbf\u8c6b\u533a'), ('321322', u'\u6cad\u9633\u53bf'), ('321323', u'\u6cd7\u9633\u53bf'), ('321324', u'\u6cd7\u6d2a\u53bf'), ('330000', u'\u6d59\u6c5f\u7701'), ('330100', u'\u676d\u5dde\u5e02'), ('330101', u'\u5e02\u8f96\u533a'), ('330102', u'\u4e0a\u57ce\u533a'), ('330103', u'\u4e0b\u57ce\u533a'), ('330104', u'\u6c5f\u5e72\u533a'), ('330105', u'\u62f1\u5885\u533a'), ('330106', u'\u897f\u6e56\u533a'), ('330108', u'\u6ee8\u6c5f\u533a'), ('330109', u'\u8427\u5c71\u533a'), ('330110', u'\u4f59\u676d\u533a'), ('330122', u'\u6850\u5e90\u53bf'), ('330127', u'\u6df3\u5b89\u53bf'), ('330182', u'\u5efa\u5fb7\u5e02'), ('330183', u'\u5bcc\u9633\u5e02'), ('330185', u'\u4e34\u5b89\u5e02'), ('330200', u'\u5b81\u6ce2\u5e02'), ('330201', u'\u5e02\u8f96\u533a'), ('330203', u'\u6d77\u66d9\u533a'), ('330204', u'\u6c5f\u4e1c\u533a'), ('330205', u'\u6c5f\u5317\u533a'), ('330206', u'\u5317\u4ed1\u533a'), ('330211', u'\u9547\u6d77\u533a'), ('330212', u'\u911e\u5dde\u533a'), ('330225', u'\u8c61\u5c71\u53bf'), ('330226', u'\u5b81\u6d77\u53bf'), ('330281', u'\u4f59\u59da\u5e02'), ('330282', u'\u6148\u6eaa\u5e02'), ('330283', u'\u5949\u5316\u5e02'), ('330300', u'\u6e29\u5dde\u5e02'), ('330301', u'\u5e02\u8f96\u533a'), ('330302', u'\u9e7f\u57ce\u533a'), ('330303', u'\u9f99\u6e7e\u533a'), ('330304', u'\u74ef\u6d77\u533a'), ('330322', u'\u6d1e\u5934\u53bf'), ('330324', u'\u6c38\u5609\u53bf'), ('330326', u'\u5e73\u9633\u53bf'), ('330327', u'\u82cd\u5357\u53bf'), ('330328', u'\u6587\u6210\u53bf'), ('330329', u'\u6cf0\u987a\u53bf'), ('330381', u'\u745e\u5b89\u5e02'), ('330382', u'\u4e50\u6e05\u5e02'), ('330400', u'\u5609\u5174\u5e02'), ('330401', u'\u5e02\u8f96\u533a'), ('330402', u'\u5357\u6e56\u533a'), ('330411', u'\u79c0\u6d32\u533a'), ('330421', u'\u5609\u5584\u53bf'), ('330424', u'\u6d77\u76d0\u53bf'), ('330481', u'\u6d77\u5b81\u5e02'), ('330482', u'\u5e73\u6e56\u5e02'), ('330483', u'\u6850\u4e61\u5e02'), ('330500', u'\u6e56\u5dde\u5e02'), ('330501', u'\u5e02\u8f96\u533a'), ('330502', u'\u5434\u5174\u533a'), ('330503', u'\u5357\u6d54\u533a'), ('330521', u'\u5fb7\u6e05\u53bf'), ('330522', u'\u957f\u5174\u53bf'), ('330523', u'\u5b89\u5409\u53bf'), ('330600', u'\u7ecd\u5174\u5e02'), ('330601', u'\u5e02\u8f96\u533a'), ('330602', u'\u8d8a\u57ce\u533a'), ('330621', u'\u7ecd\u5174\u53bf'), ('330624', u'\u65b0\u660c\u53bf'), ('330681', u'\u8bf8\u66a8\u5e02'), ('330682', u'\u4e0a\u865e\u5e02'), ('330683', u'\u5d4a\u5dde\u5e02'), ('330700', u'\u91d1\u534e\u5e02'), ('330701', u'\u5e02\u8f96\u533a'), ('330702', u'\u5a7a\u57ce\u533a'), ('330703', u'\u91d1\u4e1c\u533a'), ('330723', u'\u6b66\u4e49\u53bf'), ('330726', u'\u6d66\u6c5f\u53bf'), ('330727', u'\u78d0\u5b89\u53bf'), ('330781', u'\u5170\u6eaa\u5e02'), ('330782', u'\u4e49\u4e4c\u5e02'), ('330783', u'\u4e1c\u9633\u5e02'), ('330784', u'\u6c38\u5eb7\u5e02'), ('330800', u'\u8862\u5dde\u5e02'), ('330801', u'\u5e02\u8f96\u533a'), ('330802', u'\u67ef\u57ce\u533a'), ('330803', u'\u8862\u6c5f\u533a'), ('330822', u'\u5e38\u5c71\u53bf'), ('330824', u'\u5f00\u5316\u53bf'), ('330825', u'\u9f99\u6e38\u53bf'), ('330881', u'\u6c5f\u5c71\u5e02'), ('330900', u'\u821f\u5c71\u5e02'), ('330901', u'\u5e02\u8f96\u533a'), ('330902', u'\u5b9a\u6d77\u533a'), ('330903', u'\u666e\u9640\u533a'), ('330921', u'\u5cb1\u5c71\u53bf'), ('330922', u'\u5d4a\u6cd7\u53bf'), ('331000', u'\u53f0\u5dde\u5e02'), ('331001', u'\u5e02\u8f96\u533a'), ('331002', u'\u6912\u6c5f\u533a'), ('331003', u'\u9ec4\u5ca9\u533a'), ('331004', u'\u8def\u6865\u533a'), ('331021', u'\u7389\u73af\u53bf'), ('331022', u'\u4e09\u95e8\u53bf'), ('331023', u'\u5929\u53f0\u53bf'), ('331024', u'\u4ed9\u5c45\u53bf'), ('331081', u'\u6e29\u5cad\u5e02'), ('331082', u'\u4e34\u6d77\u5e02'), ('331100', u'\u4e3d\u6c34\u5e02'), ('331101', u'\u5e02\u8f96\u533a'), ('331102', u'\u83b2\u90fd\u533a'), ('331121', u'\u9752\u7530\u53bf'), ('331122', u'\u7f19\u4e91\u53bf'), ('331123', u'\u9042\u660c\u53bf'), ('331124', u'\u677e\u9633\u53bf'), ('331125', u'\u4e91\u548c\u53bf'), ('331126', u'\u5e86\u5143\u53bf'), ('331127', u'\u666f\u5b81\u7572\u65cf\u81ea\u6cbb\u53bf'), ('331181', u'\u9f99\u6cc9\u5e02'), ('340000', u'\u5b89\u5fbd\u7701'), ('340100', u'\u5408\u80a5\u5e02'), ('340101', u'\u5e02\u8f96\u533a'), ('340102', u'\u7476\u6d77\u533a'), ('340103', u'\u5e90\u9633\u533a'), ('340104', u'\u8700\u5c71\u533a'), ('340111', u'\u5305\u6cb3\u533a'), ('340121', u'\u957f\u4e30\u53bf'), ('340122', u'\u80a5\u4e1c\u53bf'), ('340123', u'\u80a5\u897f\u53bf'), ('340124', u'\u5e90\u6c5f\u53bf'), ('340181', u'\u5de2\u6e56\u5e02'), ('340200', u'\u829c\u6e56\u5e02'), ('340201', u'\u5e02\u8f96\u533a'), ('340202', u'\u955c\u6e56\u533a'), ('340203', u'\u5f0b\u6c5f\u533a'), ('340207', u'\u9e20\u6c5f\u533a'), ('340208', u'\u4e09\u5c71\u533a'), ('340221', u'\u829c\u6e56\u53bf'), ('340222', u'\u7e41\u660c\u53bf'), ('340223', u'\u5357\u9675\u53bf'), ('340225', u'\u65e0\u4e3a\u53bf'), ('340300', u'\u868c\u57e0\u5e02'), ('340301', u'\u5e02\u8f96\u533a'), ('340302', u'\u9f99\u5b50\u6e56\u533a'), ('340303', u'\u868c\u5c71\u533a'), ('340304', u'\u79b9\u4f1a\u533a'), ('340311', u'\u6dee\u4e0a\u533a'), ('340321', u'\u6000\u8fdc\u53bf'), ('340322', u'\u4e94\u6cb3\u53bf'), ('340323', u'\u56fa\u9547\u53bf'), ('340400', u'\u6dee\u5357\u5e02'), ('340401', u'\u5e02\u8f96\u533a'), ('340402', u'\u5927\u901a\u533a'), ('340403', u'\u7530\u5bb6\u5eb5\u533a'), ('340404', u'\u8c22\u5bb6\u96c6\u533a'), ('340405', u'\u516b\u516c\u5c71\u533a'), ('340406', u'\u6f58\u96c6\u533a'), ('340421', u'\u51e4\u53f0\u53bf'), ('340500', u'\u9a6c\u978d\u5c71\u5e02'), ('340501', u'\u5e02\u8f96\u533a'), ('340503', u'\u82b1\u5c71\u533a'), ('340504', u'\u96e8\u5c71\u533a'), ('340506', u'\u535a\u671b\u533a'), ('340521', u'\u5f53\u6d82\u53bf'), ('340522', u'\u542b\u5c71\u53bf'), ('340523', u'\u548c\u53bf'), ('340600', u'\u6dee\u5317\u5e02'), ('340601', u'\u5e02\u8f96\u533a'), ('340602', u'\u675c\u96c6\u533a'), ('340603', u'\u76f8\u5c71\u533a'), ('340604', u'\u70c8\u5c71\u533a'), ('340621', u'\u6fc9\u6eaa\u53bf'), ('340700', u'\u94dc\u9675\u5e02'), ('340701', u'\u5e02\u8f96\u533a'), ('340702', u'\u94dc\u5b98\u5c71\u533a'), ('340703', u'\u72ee\u5b50\u5c71\u533a'), ('340711', u'\u90ca\u533a'), ('340721', u'\u94dc\u9675\u53bf'), ('340800', u'\u5b89\u5e86\u5e02'), ('340801', u'\u5e02\u8f96\u533a'), ('340802', u'\u8fce\u6c5f\u533a'), ('340803', u'\u5927\u89c2\u533a'), ('340811', u'\u5b9c\u79c0\u533a'), ('340822', u'\u6000\u5b81\u53bf'), ('340823', u'\u679e\u9633\u53bf'), ('340824', u'\u6f5c\u5c71\u53bf'), ('340825', u'\u592a\u6e56\u53bf'), ('340826', u'\u5bbf\u677e\u53bf'), ('340827', u'\u671b\u6c5f\u53bf'), ('340828', u'\u5cb3\u897f\u53bf'), ('340881', u'\u6850\u57ce\u5e02'), ('341000', u'\u9ec4\u5c71\u5e02'), ('341001', u'\u5e02\u8f96\u533a'), ('341002', u'\u5c6f\u6eaa\u533a'), ('341003', u'\u9ec4\u5c71\u533a'), ('341004', u'\u5fbd\u5dde\u533a'), ('341021', u'\u6b59\u53bf'), ('341022', u'\u4f11\u5b81\u53bf'), ('341023', u'\u9edf\u53bf'), ('341024', u'\u7941\u95e8\u53bf'), ('341100', u'\u6ec1\u5dde\u5e02'), ('341101', u'\u5e02\u8f96\u533a'), ('341102', u'\u7405\u740a\u533a'), ('341103', u'\u5357\u8c2f\u533a'), ('341122', u'\u6765\u5b89\u53bf'), ('341124', u'\u5168\u6912\u53bf'), ('341125', u'\u5b9a\u8fdc\u53bf'), ('341126', u'\u51e4\u9633\u53bf'), ('341181', u'\u5929\u957f\u5e02'), ('341182', u'\u660e\u5149\u5e02'), ('341200', u'\u961c\u9633\u5e02'), ('341201', u'\u5e02\u8f96\u533a'), ('341202', u'\u988d\u5dde\u533a'), ('341203', u'\u988d\u4e1c\u533a'), ('341204', u'\u988d\u6cc9\u533a'), ('341221', u'\u4e34\u6cc9\u53bf'), ('341222', u'\u592a\u548c\u53bf'), ('341225', u'\u961c\u5357\u53bf'), ('341226', u'\u988d\u4e0a\u53bf'), ('341282', u'\u754c\u9996\u5e02'), ('341300', u'\u5bbf\u5dde\u5e02'), ('341301', u'\u5e02\u8f96\u533a'), ('341302', u'\u57c7\u6865\u533a'), ('341321', u'\u7800\u5c71\u53bf'), ('341322', u'\u8427\u53bf'), ('341323', u'\u7075\u74a7\u53bf'), ('341324', u'\u6cd7\u53bf'), ('341500', u'\u516d\u5b89\u5e02'), ('341501', u'\u5e02\u8f96\u533a'), ('341502', u'\u91d1\u5b89\u533a'), ('341503', u'\u88d5\u5b89\u533a'), ('341521', u'\u5bff\u53bf'), ('341522', u'\u970d\u90b1\u53bf'), ('341523', u'\u8212\u57ce\u53bf'), ('341524', u'\u91d1\u5be8\u53bf'), ('341525', u'\u970d\u5c71\u53bf'), ('341600', u'\u4eb3\u5dde\u5e02'), ('341601', u'\u5e02\u8f96\u533a'), ('341602', u'\u8c2f\u57ce\u533a'), ('341621', u'\u6da1\u9633\u53bf'), ('341622', u'\u8499\u57ce\u53bf'), ('341623', u'\u5229\u8f9b\u53bf'), ('341700', u'\u6c60\u5dde\u5e02'), ('341701', u'\u5e02\u8f96\u533a'), ('341702', u'\u8d35\u6c60\u533a'), ('341721', u'\u4e1c\u81f3\u53bf'), ('341722', u'\u77f3\u53f0\u53bf'), ('341723', u'\u9752\u9633\u53bf'), ('341800', u'\u5ba3\u57ce\u5e02'), ('341801', u'\u5e02\u8f96\u533a'), ('341802', u'\u5ba3\u5dde\u533a'), ('341821', u'\u90ce\u6eaa\u53bf'), ('341822', u'\u5e7f\u5fb7\u53bf'), ('341823', u'\u6cfe\u53bf'), ('341824', u'\u7ee9\u6eaa\u53bf'), ('341825', u'\u65cc\u5fb7\u53bf'), ('341881', u'\u5b81\u56fd\u5e02'), ('350000', u'\u798f\u5efa\u7701'), ('350100', u'\u798f\u5dde\u5e02'), ('350101', u'\u5e02\u8f96\u533a'), ('350102', u'\u9f13\u697c\u533a'), ('350103', u'\u53f0\u6c5f\u533a'), ('350104', u'\u4ed3\u5c71\u533a'), ('350105', u'\u9a6c\u5c3e\u533a'), ('350111', u'\u664b\u5b89\u533a'), ('350121', u'\u95fd\u4faf\u53bf'), ('350122', u'\u8fde\u6c5f\u53bf'), ('350123', u'\u7f57\u6e90\u53bf'), ('350124', u'\u95fd\u6e05\u53bf'), ('350125', u'\u6c38\u6cf0\u53bf'), ('350128', u'\u5e73\u6f6d\u53bf'), ('350181', u'\u798f\u6e05\u5e02'), ('350182', u'\u957f\u4e50\u5e02'), ('350200', u'\u53a6\u95e8\u5e02'), ('350201', u'\u5e02\u8f96\u533a'), ('350203', u'\u601d\u660e\u533a'), ('350205', u'\u6d77\u6ca7\u533a'), ('350206', u'\u6e56\u91cc\u533a'), ('350211', u'\u96c6\u7f8e\u533a'), ('350212', u'\u540c\u5b89\u533a'), ('350213', u'\u7fd4\u5b89\u533a'), ('350300', u'\u8386\u7530\u5e02'), ('350301', u'\u5e02\u8f96\u533a'), ('350302', u'\u57ce\u53a2\u533a'), ('350303', u'\u6db5\u6c5f\u533a'), ('350304', u'\u8354\u57ce\u533a'), ('350305', u'\u79c0\u5c7f\u533a'), ('350322', u'\u4ed9\u6e38\u53bf'), ('350400', u'\u4e09\u660e\u5e02'), ('350401', u'\u5e02\u8f96\u533a'), ('350402', u'\u6885\u5217\u533a'), ('350403', u'\u4e09\u5143\u533a'), ('350421', u'\u660e\u6eaa\u53bf'), ('350423', u'\u6e05\u6d41\u53bf'), ('350424', u'\u5b81\u5316\u53bf'), ('350425', u'\u5927\u7530\u53bf'), ('350426', u'\u5c24\u6eaa\u53bf'), ('350427', u'\u6c99\u53bf'), ('350428', u'\u5c06\u4e50\u53bf'), ('350429', u'\u6cf0\u5b81\u53bf'), ('350430', u'\u5efa\u5b81\u53bf'), ('350481', u'\u6c38\u5b89\u5e02'), ('350500', u'\u6cc9\u5dde\u5e02'), ('350501', u'\u5e02\u8f96\u533a'), ('350502', u'\u9ca4\u57ce\u533a'), ('350503', u'\u4e30\u6cfd\u533a'), ('350504', u'\u6d1b\u6c5f\u533a'), ('350505', u'\u6cc9\u6e2f\u533a'), ('350521', u'\u60e0\u5b89\u53bf'), ('350524', u'\u5b89\u6eaa\u53bf'), ('350525', u'\u6c38\u6625\u53bf'), ('350526', u'\u5fb7\u5316\u53bf'), ('350527', u'\u91d1\u95e8\u53bf'), ('350581', u'\u77f3\u72ee\u5e02'), ('350582', u'\u664b\u6c5f\u5e02'), ('350583', u'\u5357\u5b89\u5e02'), ('350600', u'\u6f33\u5dde\u5e02'), ('350601', u'\u5e02\u8f96\u533a'), ('350602', u'\u8297\u57ce\u533a'), ('350603', u'\u9f99\u6587\u533a'), ('350622', u'\u4e91\u9704\u53bf'), ('350623', u'\u6f33\u6d66\u53bf'), ('350624', u'\u8bcf\u5b89\u53bf'), ('350625', u'\u957f\u6cf0\u53bf'), ('350626', u'\u4e1c\u5c71\u53bf'), ('350627', u'\u5357\u9756\u53bf'), ('350628', u'\u5e73\u548c\u53bf'), ('350629', u'\u534e\u5b89\u53bf'), ('350681', u'\u9f99\u6d77\u5e02'), ('350700', u'\u5357\u5e73\u5e02'), ('350701', u'\u5e02\u8f96\u533a'), ('350702', u'\u5ef6\u5e73\u533a'), ('350721', u'\u987a\u660c\u53bf'), ('350722', u'\u6d66\u57ce\u53bf'), ('350723', u'\u5149\u6cfd\u53bf'), ('350724', u'\u677e\u6eaa\u53bf'), ('350725', u'\u653f\u548c\u53bf'), ('350781', u'\u90b5\u6b66\u5e02'), ('350782', u'\u6b66\u5937\u5c71\u5e02'), ('350783', u'\u5efa\u74ef\u5e02'), ('350784', u'\u5efa\u9633\u5e02'), ('350800', u'\u9f99\u5ca9\u5e02'), ('350801', u'\u5e02\u8f96\u533a'), ('350802', u'\u65b0\u7f57\u533a'), ('350821', u'\u957f\u6c40\u53bf'), ('350822', u'\u6c38\u5b9a\u53bf'), ('350823', u'\u4e0a\u676d\u53bf'), ('350824', u'\u6b66\u5e73\u53bf'), ('350825', u'\u8fde\u57ce\u53bf'), ('350881', u'\u6f33\u5e73\u5e02'), ('350900', u'\u5b81\u5fb7\u5e02'), ('350901', u'\u5e02\u8f96\u533a'), ('350902', u'\u8549\u57ce\u533a'), ('350921', u'\u971e\u6d66\u53bf'), ('350922', u'\u53e4\u7530\u53bf'), ('350923', u'\u5c4f\u5357\u53bf'), ('350924', u'\u5bff\u5b81\u53bf'), ('350925', u'\u5468\u5b81\u53bf'), ('350926', u'\u67d8\u8363\u53bf'), ('350981', u'\u798f\u5b89\u5e02'), ('350982', u'\u798f\u9f0e\u5e02'), ('360000', u'\u6c5f\u897f\u7701'), ('360100', u'\u5357\u660c\u5e02'), ('360101', u'\u5e02\u8f96\u533a'), ('360102', u'\u4e1c\u6e56\u533a'), ('360103', u'\u897f\u6e56\u533a'), ('360104', u'\u9752\u4e91\u8c31\u533a'), ('360105', u'\u6e7e\u91cc\u533a'), ('360111', u'\u9752\u5c71\u6e56\u533a'), ('360121', u'\u5357\u660c\u53bf'), ('360122', u'\u65b0\u5efa\u53bf'), ('360123', u'\u5b89\u4e49\u53bf'), ('360124', u'\u8fdb\u8d24\u53bf'), ('360200', u'\u666f\u5fb7\u9547\u5e02'), ('360201', u'\u5e02\u8f96\u533a'), ('360202', u'\u660c\u6c5f\u533a'), ('360203', u'\u73e0\u5c71\u533a'), ('360222', u'\u6d6e\u6881\u53bf'), ('360281', u'\u4e50\u5e73\u5e02'), ('360300', u'\u840d\u4e61\u5e02'), ('360301', u'\u5e02\u8f96\u533a'), ('360302', u'\u5b89\u6e90\u533a'), ('360313', u'\u6e58\u4e1c\u533a'), ('360321', u'\u83b2\u82b1\u53bf'), ('360322', u'\u4e0a\u6817\u53bf'), ('360323', u'\u82a6\u6eaa\u53bf'), ('360400', u'\u4e5d\u6c5f\u5e02'), ('360401', u'\u5e02\u8f96\u533a'), ('360402', u'\u5e90\u5c71\u533a'), ('360403', u'\u6d54\u9633\u533a'), ('360421', u'\u4e5d\u6c5f\u53bf'), ('360423', u'\u6b66\u5b81\u53bf'), ('360424', u'\u4fee\u6c34\u53bf'), ('360425', u'\u6c38\u4fee\u53bf'), ('360426', u'\u5fb7\u5b89\u53bf'), ('360427', u'\u661f\u5b50\u53bf'), ('360428', u'\u90fd\u660c\u53bf'), ('360429', u'\u6e56\u53e3\u53bf'), ('360430', u'\u5f6d\u6cfd\u53bf'), ('360481', u'\u745e\u660c\u5e02'), ('360482', u'\u5171\u9752\u57ce\u5e02'), ('360500', u'\u65b0\u4f59\u5e02'), ('360501', u'\u5e02\u8f96\u533a'), ('360502', u'\u6e1d\u6c34\u533a'), ('360521', u'\u5206\u5b9c\u53bf'), ('360600', u'\u9e70\u6f6d\u5e02'), ('360601', u'\u5e02\u8f96\u533a'), ('360602', u'\u6708\u6e56\u533a'), ('360622', u'\u4f59\u6c5f\u53bf'), ('360681', u'\u8d35\u6eaa\u5e02'), ('360700', u'\u8d63\u5dde\u5e02'), ('360701', u'\u5e02\u8f96\u533a'), ('360702', u'\u7ae0\u8d21\u533a'), ('360721', u'\u8d63\u53bf'), ('360722', u'\u4fe1\u4e30\u53bf'), ('360723', u'\u5927\u4f59\u53bf'), ('360724', u'\u4e0a\u72b9\u53bf'), ('360725', u'\u5d07\u4e49\u53bf'), ('360726', u'\u5b89\u8fdc\u53bf'), ('360727', u'\u9f99\u5357\u53bf'), ('360728', u'\u5b9a\u5357\u53bf'), ('360729', u'\u5168\u5357\u53bf'), ('360730', u'\u5b81\u90fd\u53bf'), ('360731', u'\u4e8e\u90fd\u53bf'), ('360732', u'\u5174\u56fd\u53bf'), ('360733', u'\u4f1a\u660c\u53bf'), ('360734', u'\u5bfb\u4e4c\u53bf'), ('360735', u'\u77f3\u57ce\u53bf'), ('360781', u'\u745e\u91d1\u5e02'), ('360782', u'\u5357\u5eb7\u5e02'), ('360800', u'\u5409\u5b89\u5e02'), ('360801', u'\u5e02\u8f96\u533a'), ('360802', u'\u5409\u5dde\u533a'), ('360803', u'\u9752\u539f\u533a'), ('360821', u'\u5409\u5b89\u53bf'), ('360822', u'\u5409\u6c34\u53bf'), ('360823', u'\u5ce1\u6c5f\u53bf'), ('360824', u'\u65b0\u5e72\u53bf'), ('360825', u'\u6c38\u4e30\u53bf'), ('360826', u'\u6cf0\u548c\u53bf'), ('360827', u'\u9042\u5ddd\u53bf'), ('360828', u'\u4e07\u5b89\u53bf'), ('360829', u'\u5b89\u798f\u53bf'), ('360830', u'\u6c38\u65b0\u53bf'), ('360881', u'\u4e95\u5188\u5c71\u5e02'), ('360900', u'\u5b9c\u6625\u5e02'), ('360901', u'\u5e02\u8f96\u533a'), ('360902', u'\u8881\u5dde\u533a'), ('360921', u'\u5949\u65b0\u53bf'), ('360922', u'\u4e07\u8f7d\u53bf'), ('360923', u'\u4e0a\u9ad8\u53bf'), ('360924', u'\u5b9c\u4e30\u53bf'), ('360925', u'\u9756\u5b89\u53bf'), ('360926', u'\u94dc\u9f13\u53bf'), ('360981', u'\u4e30\u57ce\u5e02'), ('360982', u'\u6a1f\u6811\u5e02'), ('360983', u'\u9ad8\u5b89\u5e02'), ('361000', u'\u629a\u5dde\u5e02'), ('361001', u'\u5e02\u8f96\u533a'), ('361002', u'\u4e34\u5ddd\u533a'), ('361021', u'\u5357\u57ce\u53bf'), ('361022', u'\u9ece\u5ddd\u53bf'), ('361023', u'\u5357\u4e30\u53bf'), ('361024', u'\u5d07\u4ec1\u53bf'), ('361025', u'\u4e50\u5b89\u53bf'), ('361026', u'\u5b9c\u9ec4\u53bf'), ('361027', u'\u91d1\u6eaa\u53bf'), ('361028', u'\u8d44\u6eaa\u53bf'), ('361029', u'\u4e1c\u4e61\u53bf'), ('361030', u'\u5e7f\u660c\u53bf'), ('361100', u'\u4e0a\u9976\u5e02'), ('361101', u'\u5e02\u8f96\u533a'), ('361102', u'\u4fe1\u5dde\u533a'), ('361121', u'\u4e0a\u9976\u53bf'), ('361122', u'\u5e7f\u4e30\u53bf'), ('361123', u'\u7389\u5c71\u53bf'), ('361124', u'\u94c5\u5c71\u53bf'), ('361125', u'\u6a2a\u5cf0\u53bf'), ('361126', u'\u5f0b\u9633\u53bf'), ('361127', u'\u4f59\u5e72\u53bf'), ('361128', u'\u9131\u9633\u53bf'), ('361129', u'\u4e07\u5e74\u53bf'), ('361130', u'\u5a7a\u6e90\u53bf'), ('361181', u'\u5fb7\u5174\u5e02'), ('370000', u'\u5c71\u4e1c\u7701'), ('370100', u'\u6d4e\u5357\u5e02'), ('370101', u'\u5e02\u8f96\u533a'), ('370102', u'\u5386\u4e0b\u533a'), ('370103', u'\u5e02\u4e2d\u533a'), ('370104', u'\u69d0\u836b\u533a'), ('370105', u'\u5929\u6865\u533a'), ('370112', u'\u5386\u57ce\u533a'), ('370113', u'\u957f\u6e05\u533a'), ('370124', u'\u5e73\u9634\u53bf'), ('370125', u'\u6d4e\u9633\u53bf'), ('370126', u'\u5546\u6cb3\u53bf'), ('370181', u'\u7ae0\u4e18\u5e02'), ('370200', u'\u9752\u5c9b\u5e02'), ('370201', u'\u5e02\u8f96\u533a'), ('370202', u'\u5e02\u5357\u533a'), ('370203', u'\u5e02\u5317\u533a'), ('370211', u'\u9ec4\u5c9b\u533a'), ('370212', u'\u5d02\u5c71\u533a'), ('370213', u'\u674e\u6ca7\u533a'), ('370214', u'\u57ce\u9633\u533a'), ('370281', u'\u80f6\u5dde\u5e02'), ('370282', u'\u5373\u58a8\u5e02'), ('370283', u'\u5e73\u5ea6\u5e02'), ('370285', u'\u83b1\u897f\u5e02'), ('370300', u'\u6dc4\u535a\u5e02'), ('370301', u'\u5e02\u8f96\u533a'), ('370302', u'\u6dc4\u5ddd\u533a'), ('370303', u'\u5f20\u5e97\u533a'), ('370304', u'\u535a\u5c71\u533a'), ('370305', u'\u4e34\u6dc4\u533a'), ('370306', u'\u5468\u6751\u533a'), ('370321', u'\u6853\u53f0\u53bf'), ('370322', u'\u9ad8\u9752\u53bf'), ('370323', u'\u6c82\u6e90\u53bf'), ('370400', u'\u67a3\u5e84\u5e02'), ('370401', u'\u5e02\u8f96\u533a'), ('370402', u'\u5e02\u4e2d\u533a'), ('370403', u'\u859b\u57ce\u533a'), ('370404', u'\u5cc4\u57ce\u533a'), ('370405', u'\u53f0\u513f\u5e84\u533a'), ('370406', u'\u5c71\u4ead\u533a'), ('370481', u'\u6ed5\u5dde\u5e02'), ('370500', u'\u4e1c\u8425\u5e02'), ('370501', u'\u5e02\u8f96\u533a'), ('370502', u'\u4e1c\u8425\u533a'), ('370503', u'\u6cb3\u53e3\u533a'), ('370521', u'\u57a6\u5229\u53bf'), ('370522', u'\u5229\u6d25\u53bf'), ('370523', u'\u5e7f\u9976\u53bf'), ('370600', u'\u70df\u53f0\u5e02'), ('370601', u'\u5e02\u8f96\u533a'), ('370602', u'\u829d\u7f58\u533a'), ('370611', u'\u798f\u5c71\u533a'), ('370612', u'\u725f\u5e73\u533a'), ('370613', u'\u83b1\u5c71\u533a'), ('370634', u'\u957f\u5c9b\u53bf'), ('370681', u'\u9f99\u53e3\u5e02'), ('370682', u'\u83b1\u9633\u5e02'), ('370683', u'\u83b1\u5dde\u5e02'), ('370684', u'\u84ec\u83b1\u5e02'), ('370685', u'\u62db\u8fdc\u5e02'), ('370686', u'\u6816\u971e\u5e02'), ('370687', u'\u6d77\u9633\u5e02'), ('370700', u'\u6f4d\u574a\u5e02'), ('370701', u'\u5e02\u8f96\u533a'), ('370702', u'\u6f4d\u57ce\u533a'), ('370703', u'\u5bd2\u4ead\u533a'), ('370704', u'\u574a\u5b50\u533a'), ('370705', u'\u594e\u6587\u533a'), ('370724', u'\u4e34\u6710\u53bf'), ('370725', u'\u660c\u4e50\u53bf'), ('370781', u'\u9752\u5dde\u5e02'), ('370782', u'\u8bf8\u57ce\u5e02'), ('370783', u'\u5bff\u5149\u5e02'), ('370784', u'\u5b89\u4e18\u5e02'), ('370785', u'\u9ad8\u5bc6\u5e02'), ('370786', u'\u660c\u9091\u5e02'), ('370800', u'\u6d4e\u5b81\u5e02'), ('370801', u'\u5e02\u8f96\u533a'), ('370802', u'\u5e02\u4e2d\u533a'), ('370811', u'\u4efb\u57ce\u533a'), ('370826', u'\u5fae\u5c71\u53bf'), ('370827', u'\u9c7c\u53f0\u53bf'), ('370828', u'\u91d1\u4e61\u53bf'), ('370829', u'\u5609\u7965\u53bf'), ('370830', u'\u6c76\u4e0a\u53bf'), ('370831', u'\u6cd7\u6c34\u53bf'), ('370832', u'\u6881\u5c71\u53bf'), ('370881', u'\u66f2\u961c\u5e02'), ('370882', u'\u5156\u5dde\u5e02'), ('370883', u'\u90b9\u57ce\u5e02'), ('370900', u'\u6cf0\u5b89\u5e02'), ('370901', u'\u5e02\u8f96\u533a'), ('370902', u'\u6cf0\u5c71\u533a'), ('370911', u'\u5cb1\u5cb3\u533a'), ('370921', u'\u5b81\u9633\u53bf'), ('370923', u'\u4e1c\u5e73\u53bf'), ('370982', u'\u65b0\u6cf0\u5e02'), ('370983', u'\u80a5\u57ce\u5e02'), ('371000', u'\u5a01\u6d77\u5e02'), ('371001', u'\u5e02\u8f96\u533a'), ('371002', u'\u73af\u7fe0\u533a'), ('371081', u'\u6587\u767b\u5e02'), ('371082', u'\u8363\u6210\u5e02'), ('371083', u'\u4e73\u5c71\u5e02'), ('371100', u'\u65e5\u7167\u5e02'), ('371101', u'\u5e02\u8f96\u533a'), ('371102', u'\u4e1c\u6e2f\u533a'), ('371103', u'\u5c9a\u5c71\u533a'), ('371121', u'\u4e94\u83b2\u53bf'), ('371122', u'\u8392\u53bf'), ('371200', u'\u83b1\u829c\u5e02'), ('371201', u'\u5e02\u8f96\u533a'), ('371202', u'\u83b1\u57ce\u533a'), ('371203', u'\u94a2\u57ce\u533a'), ('371300', u'\u4e34\u6c82\u5e02'), ('371301', u'\u5e02\u8f96\u533a'), ('371302', u'\u5170\u5c71\u533a'), ('371311', u'\u7f57\u5e84\u533a'), ('371312', u'\u6cb3\u4e1c\u533a'), ('371321', u'\u6c82\u5357\u53bf'), ('371322', u'\u90ef\u57ce\u53bf'), ('371323', u'\u6c82\u6c34\u53bf'), ('371324', u'\u82cd\u5c71\u53bf'), ('371325', u'\u8d39\u53bf'), ('371326', u'\u5e73\u9091\u53bf'), ('371327', u'\u8392\u5357\u53bf'), ('371328', u'\u8499\u9634\u53bf'), ('371329', u'\u4e34\u6cad\u53bf'), ('371400', u'\u5fb7\u5dde\u5e02'), ('371401', u'\u5e02\u8f96\u533a'), ('371402', u'\u5fb7\u57ce\u533a'), ('371421', u'\u9675\u53bf'), ('371422', u'\u5b81\u6d25\u53bf'), ('371423', u'\u5e86\u4e91\u53bf'), ('371424', u'\u4e34\u9091\u53bf'), ('371425', u'\u9f50\u6cb3\u53bf'), ('371426', u'\u5e73\u539f\u53bf'), ('371427', u'\u590f\u6d25\u53bf'), ('371428', u'\u6b66\u57ce\u53bf'), ('371481', u'\u4e50\u9675\u5e02'), ('371482', u'\u79b9\u57ce\u5e02'), ('371500', u'\u804a\u57ce\u5e02'), ('371501', u'\u5e02\u8f96\u533a'), ('371502', u'\u4e1c\u660c\u5e9c\u533a'), ('371521', u'\u9633\u8c37\u53bf'), ('371522', u'\u8398\u53bf'), ('371523', u'\u830c\u5e73\u53bf'), ('371524', u'\u4e1c\u963f\u53bf'), ('371525', u'\u51a0\u53bf'), ('371526', u'\u9ad8\u5510\u53bf'), ('371581', u'\u4e34\u6e05\u5e02'), ('371600', u'\u6ee8\u5dde\u5e02'), ('371601', u'\u5e02\u8f96\u533a'), ('371602', u'\u6ee8\u57ce\u533a'), ('371621', u'\u60e0\u6c11\u53bf'), ('371622', u'\u9633\u4fe1\u53bf'), ('371623', u'\u65e0\u68e3\u53bf'), ('371624', u'\u6cbe\u5316\u53bf'), ('371625', u'\u535a\u5174\u53bf'), ('371626', u'\u90b9\u5e73\u53bf'), ('371700', u'\u83cf\u6cfd\u5e02'), ('371701', u'\u5e02\u8f96\u533a'), ('371702', u'\u7261\u4e39\u533a'), ('371721', u'\u66f9\u53bf'), ('371722', u'\u5355\u53bf'), ('371723', u'\u6210\u6b66\u53bf'), ('371724', u'\u5de8\u91ce\u53bf'), ('371725', u'\u90d3\u57ce\u53bf'), ('371726', u'\u9104\u57ce\u53bf'), ('371727', u'\u5b9a\u9676\u53bf'), ('371728', u'\u4e1c\u660e\u53bf'), ('410000', u'\u6cb3\u5357\u7701'), ('410100', u'\u90d1\u5dde\u5e02'), ('410101', u'\u5e02\u8f96\u533a'), ('410102', u'\u4e2d\u539f\u533a'), ('410103', u'\u4e8c\u4e03\u533a'), ('410104', u'\u7ba1\u57ce\u56de\u65cf\u533a'), ('410105', u'\u91d1\u6c34\u533a'), ('410106', u'\u4e0a\u8857\u533a'), ('410108', u'\u60e0\u6d4e\u533a'), ('410122', u'\u4e2d\u725f\u53bf'), ('410181', u'\u5de9\u4e49\u5e02'), ('410182', u'\u8365\u9633\u5e02'), ('410183', u'\u65b0\u5bc6\u5e02'), ('410184', u'\u65b0\u90d1\u5e02'), ('410185', u'\u767b\u5c01\u5e02'), ('410200', u'\u5f00\u5c01\u5e02'), ('410201', u'\u5e02\u8f96\u533a'), ('410202', u'\u9f99\u4ead\u533a'), ('410203', u'\u987a\u6cb3\u56de\u65cf\u533a'), ('410204', u'\u9f13\u697c\u533a'), ('410205', u'\u79b9\u738b\u53f0\u533a'), ('410211', u'\u91d1\u660e\u533a'), ('410221', u'\u675e\u53bf'), ('410222', u'\u901a\u8bb8\u53bf'), ('410223', u'\u5c09\u6c0f\u53bf'), ('410224', u'\u5f00\u5c01\u53bf'), ('410225', u'\u5170\u8003\u53bf'), ('410300', u'\u6d1b\u9633\u5e02'), ('410301', u'\u5e02\u8f96\u533a'), ('410302', u'\u8001\u57ce\u533a'), ('410303', u'\u897f\u5de5\u533a'), ('410304', u'\u700d\u6cb3\u56de\u65cf\u533a'), ('410305', u'\u6da7\u897f\u533a'), ('410306', u'\u5409\u5229\u533a'), ('410311', u'\u6d1b\u9f99\u533a'), ('410322', u'\u5b5f\u6d25\u53bf'), ('410323', u'\u65b0\u5b89\u53bf'), ('410324', u'\u683e\u5ddd\u53bf'), ('410325', u'\u5d69\u53bf'), ('410326', u'\u6c5d\u9633\u53bf'), ('410327', u'\u5b9c\u9633\u53bf'), ('410328', u'\u6d1b\u5b81\u53bf'), ('410329', u'\u4f0a\u5ddd\u53bf'), ('410381', u'\u5043\u5e08\u5e02'), ('410400', u'\u5e73\u9876\u5c71\u5e02'), ('410401', u'\u5e02\u8f96\u533a'), ('410402', u'\u65b0\u534e\u533a'), ('410403', u'\u536b\u4e1c\u533a'), ('410404', u'\u77f3\u9f99\u533a'), ('410411', u'\u6e5b\u6cb3\u533a'), ('410421', u'\u5b9d\u4e30\u53bf'), ('410422', u'\u53f6\u53bf'), ('410423', u'\u9c81\u5c71\u53bf'), ('410425', u'\u90cf\u53bf'), ('410481', u'\u821e\u94a2\u5e02'), ('410482', u'\u6c5d\u5dde\u5e02'), ('410500', u'\u5b89\u9633\u5e02'), ('410501', u'\u5e02\u8f96\u533a'), ('410502', u'\u6587\u5cf0\u533a'), ('410503', u'\u5317\u5173\u533a'), ('410505', u'\u6bb7\u90fd\u533a'), ('410506', u'\u9f99\u5b89\u533a'), ('410522', u'\u5b89\u9633\u53bf'), ('410523', u'\u6c64\u9634\u53bf'), ('410526', u'\u6ed1\u53bf'), ('410527', u'\u5185\u9ec4\u53bf'), ('410581', u'\u6797\u5dde\u5e02'), ('410600', u'\u9e64\u58c1\u5e02'), ('410601', u'\u5e02\u8f96\u533a'), ('410602', u'\u9e64\u5c71\u533a'), ('410603', u'\u5c71\u57ce\u533a'), ('410611', u'\u6dc7\u6ee8\u533a'), ('410621', u'\u6d5a\u53bf'), ('410622', u'\u6dc7\u53bf'), ('410700', u'\u65b0\u4e61\u5e02'), ('410701', u'\u5e02\u8f96\u533a'), ('410702', u'\u7ea2\u65d7\u533a'), ('410703', u'\u536b\u6ee8\u533a'), ('410704', u'\u51e4\u6cc9\u533a'), ('410711', u'\u7267\u91ce\u533a'), ('410721', u'\u65b0\u4e61\u53bf'), ('410724', u'\u83b7\u5609\u53bf'), ('410725', u'\u539f\u9633\u53bf'), ('410726', u'\u5ef6\u6d25\u53bf'), ('410727', u'\u5c01\u4e18\u53bf'), ('410728', u'\u957f\u57a3\u53bf'), ('410781', u'\u536b\u8f89\u5e02'), ('410782', u'\u8f89\u53bf\u5e02'), ('410800', u'\u7126\u4f5c\u5e02'), ('410801', u'\u5e02\u8f96\u533a'), ('410802', u'\u89e3\u653e\u533a'), ('410803', u'\u4e2d\u7ad9\u533a'), ('410804', u'\u9a6c\u6751\u533a'), ('410811', u'\u5c71\u9633\u533a'), ('410821', u'\u4fee\u6b66\u53bf'), ('410822', u'\u535a\u7231\u53bf'), ('410823', u'\u6b66\u965f\u53bf'), ('410825', u'\u6e29\u53bf'), ('410882', u'\u6c81\u9633\u5e02'), ('410883', u'\u5b5f\u5dde\u5e02'), ('410900', u'\u6fee\u9633\u5e02'), ('410901', u'\u5e02\u8f96\u533a'), ('410902', u'\u534e\u9f99\u533a'), ('410922', u'\u6e05\u4e30\u53bf'), ('410923', u'\u5357\u4e50\u53bf'), ('410926', u'\u8303\u53bf'), ('410927', u'\u53f0\u524d\u53bf'), ('410928', u'\u6fee\u9633\u53bf'), ('411000', u'\u8bb8\u660c\u5e02'), ('411001', u'\u5e02\u8f96\u533a'), ('411002', u'\u9b4f\u90fd\u533a'), ('411023', u'\u8bb8\u660c\u53bf'), ('411024', u'\u9122\u9675\u53bf'), ('411025', u'\u8944\u57ce\u53bf'), ('411081', u'\u79b9\u5dde\u5e02'), ('411082', u'\u957f\u845b\u5e02'), ('411100', u'\u6f2f\u6cb3\u5e02'), ('411101', u'\u5e02\u8f96\u533a'), ('411102', u'\u6e90\u6c47\u533a'), ('411103', u'\u90fe\u57ce\u533a'), ('411104', u'\u53ec\u9675\u533a'), ('411121', u'\u821e\u9633\u53bf'), ('411122', u'\u4e34\u988d\u53bf'), ('411200', u'\u4e09\u95e8\u5ce1\u5e02'), ('411201', u'\u5e02\u8f96\u533a'), ('411202', u'\u6e56\u6ee8\u533a'), ('411221', u'\u6e11\u6c60\u53bf'), ('411222', u'\u9655\u53bf'), ('411224', u'\u5362\u6c0f\u53bf'), ('411281', u'\u4e49\u9a6c\u5e02'), ('411282', u'\u7075\u5b9d\u5e02'), ('411300', u'\u5357\u9633\u5e02'), ('411301', u'\u5e02\u8f96\u533a'), ('411302', u'\u5b9b\u57ce\u533a'), ('411303', u'\u5367\u9f99\u533a'), ('411321', u'\u5357\u53ec\u53bf'), ('411322', u'\u65b9\u57ce\u53bf'), ('411323', u'\u897f\u5ce1\u53bf'), ('411324', u'\u9547\u5e73\u53bf'), ('411325', u'\u5185\u4e61\u53bf'), ('411326', u'\u6dc5\u5ddd\u53bf'), ('411327', u'\u793e\u65d7\u53bf'), ('411328', u'\u5510\u6cb3\u53bf'), ('411329', u'\u65b0\u91ce\u53bf'), ('411330', u'\u6850\u67cf\u53bf'), ('411381', u'\u9093\u5dde\u5e02'), ('411400', u'\u5546\u4e18\u5e02'), ('411401', u'\u5e02\u8f96\u533a'), ('411402', u'\u6881\u56ed\u533a'), ('411403', u'\u7762\u9633\u533a'), ('411421', u'\u6c11\u6743\u53bf'), ('411422', u'\u7762\u53bf'), ('411423', u'\u5b81\u9675\u53bf'), ('411424', u'\u67d8\u57ce\u53bf'), ('411425', u'\u865e\u57ce\u53bf'), ('411426', u'\u590f\u9091\u53bf'), ('411481', u'\u6c38\u57ce\u5e02'), ('411500', u'\u4fe1\u9633\u5e02'), ('411501', u'\u5e02\u8f96\u533a'), ('411502', u'\u6d49\u6cb3\u533a'), ('411503', u'\u5e73\u6865\u533a'), ('411521', u'\u7f57\u5c71\u53bf'), ('411522', u'\u5149\u5c71\u53bf'), ('411523', u'\u65b0\u53bf'), ('411524', u'\u5546\u57ce\u53bf'), ('411525', u'\u56fa\u59cb\u53bf'), ('411526', u'\u6f62\u5ddd\u53bf'), ('411527', u'\u6dee\u6ee8\u53bf'), ('411528', u'\u606f\u53bf'), ('411600', u'\u5468\u53e3\u5e02'), ('411601', u'\u5e02\u8f96\u533a'), ('411602', u'\u5ddd\u6c47\u533a'), ('411621', u'\u6276\u6c9f\u53bf'), ('411622', u'\u897f\u534e\u53bf'), ('411623', u'\u5546\u6c34\u53bf'), ('411624', u'\u6c88\u4e18\u53bf'), ('411625', u'\u90f8\u57ce\u53bf'), ('411626', u'\u6dee\u9633\u53bf'), ('411627', u'\u592a\u5eb7\u53bf'), ('411628', u'\u9e7f\u9091\u53bf'), ('411681', u'\u9879\u57ce\u5e02'), ('411700', u'\u9a7b\u9a6c\u5e97\u5e02'), ('411701', u'\u5e02\u8f96\u533a'), ('411702', u'\u9a7f\u57ce\u533a'), ('411721', u'\u897f\u5e73\u53bf'), ('411722', u'\u4e0a\u8521\u53bf'), ('411723', u'\u5e73\u8206\u53bf'), ('411724', u'\u6b63\u9633\u53bf'), ('411725', u'\u786e\u5c71\u53bf'), ('411726', u'\u6ccc\u9633\u53bf'), ('411727', u'\u6c5d\u5357\u53bf'), ('411728', u'\u9042\u5e73\u53bf'), ('411729', u'\u65b0\u8521\u53bf'), ('419000', u'\u7701\u76f4\u8f96\u53bf\u7ea7\u884c\u653f\u533a\u5212'), ('419001', u'\u6d4e\u6e90\u5e02'), ('420000', u'\u6e56\u5317\u7701'), ('420100', u'\u6b66\u6c49\u5e02'), ('420101', u'\u5e02\u8f96\u533a'), ('420102', u'\u6c5f\u5cb8\u533a'), ('420103', u'\u6c5f\u6c49\u533a'), ('420104', u'\u785a\u53e3\u533a'), ('420105', u'\u6c49\u9633\u533a'), ('420106', u'\u6b66\u660c\u533a'), ('420107', u'\u9752\u5c71\u533a'), ('420111', u'\u6d2a\u5c71\u533a'), ('420112', u'\u4e1c\u897f\u6e56\u533a'), ('420113', u'\u6c49\u5357\u533a'), ('420114', u'\u8521\u7538\u533a'), ('420115', u'\u6c5f\u590f\u533a'), ('420116', u'\u9ec4\u9642\u533a'), ('420117', u'\u65b0\u6d32\u533a'), ('420200', u'\u9ec4\u77f3\u5e02'), ('420201', u'\u5e02\u8f96\u533a'), ('420202', u'\u9ec4\u77f3\u6e2f\u533a'), ('420203', u'\u897f\u585e\u5c71\u533a'), ('420204', u'\u4e0b\u9646\u533a'), ('420205', u'\u94c1\u5c71\u533a'), ('420222', u'\u9633\u65b0\u53bf'), ('420281', u'\u5927\u51b6\u5e02'), ('420300', u'\u5341\u5830\u5e02'), ('420301', u'\u5e02\u8f96\u533a'), ('420302', u'\u8305\u7bad\u533a'), ('420303', u'\u5f20\u6e7e\u533a'), ('420321', u'\u90e7\u53bf'), ('420322', u'\u90e7\u897f\u53bf'), ('420323', u'\u7af9\u5c71\u53bf'), ('420324', u'\u7af9\u6eaa\u53bf'), ('420325', u'\u623f\u53bf'), ('420381', u'\u4e39\u6c5f\u53e3\u5e02'), ('420500', u'\u5b9c\u660c\u5e02'), ('420501', u'\u5e02\u8f96\u533a'), ('420502', u'\u897f\u9675\u533a'), ('420503', u'\u4f0d\u5bb6\u5c97\u533a'), ('420504', u'\u70b9\u519b\u533a'), ('420505', u'\u7307\u4ead\u533a'), ('420506', u'\u5937\u9675\u533a'), ('420525', u'\u8fdc\u5b89\u53bf'), ('420526', u'\u5174\u5c71\u53bf'), ('420527', u'\u79ed\u5f52\u53bf'), ('420528', u'\u957f\u9633\u571f\u5bb6\u65cf\u81ea\u6cbb\u53bf'), ('420529', u'\u4e94\u5cf0\u571f\u5bb6\u65cf\u81ea\u6cbb\u53bf'), ('420581', u'\u5b9c\u90fd\u5e02'), ('420582', u'\u5f53\u9633\u5e02'), ('420583', u'\u679d\u6c5f\u5e02'), ('420600', u'\u8944\u9633\u5e02'), ('420601', u'\u5e02\u8f96\u533a'), ('420602', u'\u8944\u57ce\u533a'), ('420606', u'\u6a0a\u57ce\u533a'), ('420607', u'\u8944\u5dde\u533a'), ('420624', u'\u5357\u6f33\u53bf'), ('420625', u'\u8c37\u57ce\u53bf'), ('420626', u'\u4fdd\u5eb7\u53bf'), ('420682', u'\u8001\u6cb3\u53e3\u5e02'), ('420683', u'\u67a3\u9633\u5e02'), ('420684', u'\u5b9c\u57ce\u5e02'), ('420700', u'\u9102\u5dde\u5e02'), ('420701', u'\u5e02\u8f96\u533a'), ('420702', u'\u6881\u5b50\u6e56\u533a'), ('420703', u'\u534e\u5bb9\u533a'), ('420704', u'\u9102\u57ce\u533a'), ('420800', u'\u8346\u95e8\u5e02'), ('420801', u'\u5e02\u8f96\u533a'), ('420802', u'\u4e1c\u5b9d\u533a'), ('420804', u'\u6387\u5200\u533a'), ('420821', u'\u4eac\u5c71\u53bf'), ('420822', u'\u6c99\u6d0b\u53bf'), ('420881', u'\u949f\u7965\u5e02'), ('420900', u'\u5b5d\u611f\u5e02'), ('420901', u'\u5e02\u8f96\u533a'), ('420902', u'\u5b5d\u5357\u533a'), ('420921', u'\u5b5d\u660c\u53bf'), ('420922', u'\u5927\u609f\u53bf'), ('420923', u'\u4e91\u68a6\u53bf'), ('420981', u'\u5e94\u57ce\u5e02'), ('420982', u'\u5b89\u9646\u5e02'), ('420984', u'\u6c49\u5ddd\u5e02'), ('421000', u'\u8346\u5dde\u5e02'), ('421001', u'\u5e02\u8f96\u533a'), ('421002', u'\u6c99\u5e02\u533a'), ('421003', u'\u8346\u5dde\u533a'), ('421022', u'\u516c\u5b89\u53bf'), ('421023', u'\u76d1\u5229\u53bf'), ('421024', u'\u6c5f\u9675\u53bf'), ('421081', u'\u77f3\u9996\u5e02'), ('421083', u'\u6d2a\u6e56\u5e02'), ('421087', u'\u677e\u6ecb\u5e02'), ('421100', u'\u9ec4\u5188\u5e02'), ('421101', u'\u5e02\u8f96\u533a'), ('421102', u'\u9ec4\u5dde\u533a'), ('421121', u'\u56e2\u98ce\u53bf'), ('421122', u'\u7ea2\u5b89\u53bf'), ('421123', u'\u7f57\u7530\u53bf'), ('421124', u'\u82f1\u5c71\u53bf'), ('421125', u'\u6d60\u6c34\u53bf'), ('421126', u'\u8572\u6625\u53bf'), ('421127', u'\u9ec4\u6885\u53bf'), ('421181', u'\u9ebb\u57ce\u5e02'), ('421182', u'\u6b66\u7a74\u5e02'), ('421200', u'\u54b8\u5b81\u5e02'), ('421201', u'\u5e02\u8f96\u533a'), ('421202', u'\u54b8\u5b89\u533a'), ('421221', u'\u5609\u9c7c\u53bf'), ('421222', u'\u901a\u57ce\u53bf'), ('421223', u'\u5d07\u9633\u53bf'), ('421224', u'\u901a\u5c71\u53bf'), ('421281', u'\u8d64\u58c1\u5e02'), ('421300', u'\u968f\u5dde\u5e02'), ('421301', u'\u5e02\u8f96\u533a'), ('421303', u'\u66fe\u90fd\u533a'), ('421321', u'\u968f\u53bf'), ('421381', u'\u5e7f\u6c34\u5e02'), ('422800', u'\u6069\u65bd\u571f\u5bb6\u65cf\u82d7\u65cf\u81ea\u6cbb\u5dde'), ('422801', u'\u6069\u65bd\u5e02'), ('422802', u'\u5229\u5ddd\u5e02'), ('422822', u'\u5efa\u59cb\u53bf'), ('422823', u'\u5df4\u4e1c\u53bf'), ('422825', u'\u5ba3\u6069\u53bf'), ('422826', u'\u54b8\u4e30\u53bf'), ('422827', u'\u6765\u51e4\u53bf'), ('422828', u'\u9e64\u5cf0\u53bf'), ('429000', u'\u7701\u76f4\u8f96\u53bf\u7ea7\u884c\u653f\u533a\u5212'), ('429004', u'\u4ed9\u6843\u5e02'), ('429005', u'\u6f5c\u6c5f\u5e02'), ('429006', u'\u5929\u95e8\u5e02'), ('429021', u'\u795e\u519c\u67b6\u6797\u533a'), ('430000', u'\u6e56\u5357\u7701'), ('430100', u'\u957f\u6c99\u5e02'), ('430101', u'\u5e02\u8f96\u533a'), ('430102', u'\u8299\u84c9\u533a'), ('430103', u'\u5929\u5fc3\u533a'), ('430104', u'\u5cb3\u9e93\u533a'), ('430105', u'\u5f00\u798f\u533a'), ('430111', u'\u96e8\u82b1\u533a'), ('430112', u'\u671b\u57ce\u533a'), ('430121', u'\u957f\u6c99\u53bf'), ('430124', u'\u5b81\u4e61\u53bf'), ('430181', u'\u6d4f\u9633\u5e02'), ('430200', u'\u682a\u6d32\u5e02'), ('430201', u'\u5e02\u8f96\u533a'), ('430202', u'\u8377\u5858\u533a'), ('430203', u'\u82a6\u6dde\u533a'), ('430204', u'\u77f3\u5cf0\u533a'), ('430211', u'\u5929\u5143\u533a'), ('430221', u'\u682a\u6d32\u53bf'), ('430223', u'\u6538\u53bf'), ('430224', u'\u8336\u9675\u53bf'), ('430225', u'\u708e\u9675\u53bf'), ('430281', u'\u91b4\u9675\u5e02'), ('430300', u'\u6e58\u6f6d\u5e02'), ('430301', u'\u5e02\u8f96\u533a'), ('430302', u'\u96e8\u6e56\u533a'), ('430304', u'\u5cb3\u5858\u533a'), ('430321', u'\u6e58\u6f6d\u53bf'), ('430381', u'\u6e58\u4e61\u5e02'), ('430382', u'\u97f6\u5c71\u5e02'), ('430400', u'\u8861\u9633\u5e02'), ('430401', u'\u5e02\u8f96\u533a'), ('430405', u'\u73e0\u6656\u533a'), ('430406', u'\u96c1\u5cf0\u533a'), ('430407', u'\u77f3\u9f13\u533a'), ('430408', u'\u84b8\u6e58\u533a'), ('430412', u'\u5357\u5cb3\u533a'), ('430421', u'\u8861\u9633\u53bf'), ('430422', u'\u8861\u5357\u53bf'), ('430423', u'\u8861\u5c71\u53bf'), ('430424', u'\u8861\u4e1c\u53bf'), ('430426', u'\u7941\u4e1c\u53bf'), ('430481', u'\u8012\u9633\u5e02'), ('430482', u'\u5e38\u5b81\u5e02'), ('430500', u'\u90b5\u9633\u5e02'), ('430501', u'\u5e02\u8f96\u533a'), ('430502', u'\u53cc\u6e05\u533a'), ('430503', u'\u5927\u7965\u533a'), ('430511', u'\u5317\u5854\u533a'), ('430521', u'\u90b5\u4e1c\u53bf'), ('430522', u'\u65b0\u90b5\u53bf'), ('430523', u'\u90b5\u9633\u53bf'), ('430524', u'\u9686\u56de\u53bf'), ('430525', u'\u6d1e\u53e3\u53bf'), ('430527', u'\u7ee5\u5b81\u53bf'), ('430528', u'\u65b0\u5b81\u53bf'), ('430529', u'\u57ce\u6b65\u82d7\u65cf\u81ea\u6cbb\u53bf'), ('430581', u'\u6b66\u5188\u5e02'), ('430600', u'\u5cb3\u9633\u5e02'), ('430601', u'\u5e02\u8f96\u533a'), ('430602', u'\u5cb3\u9633\u697c\u533a'), ('430603', u'\u4e91\u6eaa\u533a'), ('430611', u'\u541b\u5c71\u533a'), ('430621', u'\u5cb3\u9633\u53bf'), ('430623', u'\u534e\u5bb9\u53bf'), ('430624', u'\u6e58\u9634\u53bf'), ('430626', u'\u5e73\u6c5f\u53bf'), ('430681', u'\u6c68\u7f57\u5e02'), ('430682', u'\u4e34\u6e58\u5e02'), ('430700', u'\u5e38\u5fb7\u5e02'), ('430701', u'\u5e02\u8f96\u533a'), ('430702', u'\u6b66\u9675\u533a'), ('430703', u'\u9f0e\u57ce\u533a'), ('430721', u'\u5b89\u4e61\u53bf'), ('430722', u'\u6c49\u5bff\u53bf'), ('430723', u'\u6fa7\u53bf'), ('430724', u'\u4e34\u6fa7\u53bf'), ('430725', u'\u6843\u6e90\u53bf'), ('430726', u'\u77f3\u95e8\u53bf'), ('430781', u'\u6d25\u5e02\u5e02'), ('430800', u'\u5f20\u5bb6\u754c\u5e02'), ('430801', u'\u5e02\u8f96\u533a'), ('430802', u'\u6c38\u5b9a\u533a'), ('430811', u'\u6b66\u9675\u6e90\u533a'), ('430821', u'\u6148\u5229\u53bf'), ('430822', u'\u6851\u690d\u53bf'), ('430900', u'\u76ca\u9633\u5e02'), ('430901', u'\u5e02\u8f96\u533a'), ('430902', u'\u8d44\u9633\u533a'), ('430903', u'\u8d6b\u5c71\u533a'), ('430921', u'\u5357\u53bf'), ('430922', u'\u6843\u6c5f\u53bf'), ('430923', u'\u5b89\u5316\u53bf'), ('430981', u'\u6c85\u6c5f\u5e02'), ('431000', u'\u90f4\u5dde\u5e02'), ('431001', u'\u5e02\u8f96\u533a'), ('431002', u'\u5317\u6e56\u533a'), ('431003', u'\u82cf\u4ed9\u533a'), ('431021', u'\u6842\u9633\u53bf'), ('431022', u'\u5b9c\u7ae0\u53bf'), ('431023', u'\u6c38\u5174\u53bf'), ('431024', u'\u5609\u79be\u53bf'), ('431025', u'\u4e34\u6b66\u53bf'), ('431026', u'\u6c5d\u57ce\u53bf'), ('431027', u'\u6842\u4e1c\u53bf'), ('431028', u'\u5b89\u4ec1\u53bf'), ('431081', u'\u8d44\u5174\u5e02'), ('431100', u'\u6c38\u5dde\u5e02'), ('431101', u'\u5e02\u8f96\u533a'), ('431102', u'\u96f6\u9675\u533a'), ('431103', u'\u51b7\u6c34\u6ee9\u533a'), ('431121', u'\u7941\u9633\u53bf'), ('431122', u'\u4e1c\u5b89\u53bf'), ('431123', u'\u53cc\u724c\u53bf'), ('431124', u'\u9053\u53bf'), ('431125', u'\u6c5f\u6c38\u53bf'), ('431126', u'\u5b81\u8fdc\u53bf'), ('431127', u'\u84dd\u5c71\u53bf'), ('431128', u'\u65b0\u7530\u53bf'), ('431129', u'\u6c5f\u534e\u7476\u65cf\u81ea\u6cbb\u53bf'), ('431200', u'\u6000\u5316\u5e02'), ('431201', u'\u5e02\u8f96\u533a'), ('431202', u'\u9e64\u57ce\u533a'), ('431221', u'\u4e2d\u65b9\u53bf'), ('431222', u'\u6c85\u9675\u53bf'), ('431223', u'\u8fb0\u6eaa\u53bf'), ('431224', u'\u6e86\u6d66\u53bf'), ('431225', u'\u4f1a\u540c\u53bf'), ('431226', u'\u9ebb\u9633\u82d7\u65cf\u81ea\u6cbb\u53bf'), ('431227', u'\u65b0\u6643\u4f97\u65cf\u81ea\u6cbb\u53bf'), ('431228', u'\u82b7\u6c5f\u4f97\u65cf\u81ea\u6cbb\u53bf'), ('431229', u'\u9756\u5dde\u82d7\u65cf\u4f97\u65cf\u81ea\u6cbb\u53bf'), ('431230', u'\u901a\u9053\u4f97\u65cf\u81ea\u6cbb\u53bf'), ('431281', u'\u6d2a\u6c5f\u5e02'), ('431300', u'\u5a04\u5e95\u5e02'), ('431301', u'\u5e02\u8f96\u533a'), ('431302', u'\u5a04\u661f\u533a'), ('431321', u'\u53cc\u5cf0\u53bf'), ('431322', u'\u65b0\u5316\u53bf'), ('431381', u'\u51b7\u6c34\u6c5f\u5e02'), ('431382', u'\u6d9f\u6e90\u5e02'), ('433100', u'\u6e58\u897f\u571f\u5bb6\u65cf\u82d7\u65cf\u81ea\u6cbb\u5dde'), ('433101', u'\u5409\u9996\u5e02'), ('433122', u'\u6cf8\u6eaa\u53bf'), ('433123', u'\u51e4\u51f0\u53bf'), ('433124', u'\u82b1\u57a3\u53bf'), ('433125', u'\u4fdd\u9756\u53bf'), ('433126', u'\u53e4\u4e08\u53bf'), ('433127', u'\u6c38\u987a\u53bf'), ('433130', u'\u9f99\u5c71\u53bf'), ('440000', u'\u5e7f\u4e1c\u7701'), ('440100', u'\u5e7f\u5dde\u5e02'), ('440101', u'\u5e02\u8f96\u533a'), ('440103', u'\u8354\u6e7e\u533a'), ('440104', u'\u8d8a\u79c0\u533a'), ('440105', u'\u6d77\u73e0\u533a'), ('440106', u'\u5929\u6cb3\u533a'), ('440111', u'\u767d\u4e91\u533a'), ('440112', u'\u9ec4\u57d4\u533a'), ('440113', u'\u756a\u79ba\u533a'), ('440114', u'\u82b1\u90fd\u533a'), ('440115', u'\u5357\u6c99\u533a'), ('440116', u'\u841d\u5c97\u533a'), ('440183', u'\u589e\u57ce\u5e02'), ('440184', u'\u4ece\u5316\u5e02'), ('440200', u'\u97f6\u5173\u5e02'), ('440201', u'\u5e02\u8f96\u533a'), ('440203', u'\u6b66\u6c5f\u533a'), ('440204', u'\u6d48\u6c5f\u533a'), ('440205', u'\u66f2\u6c5f\u533a'), ('440222', u'\u59cb\u5174\u53bf'), ('440224', u'\u4ec1\u5316\u53bf'), ('440229', u'\u7fc1\u6e90\u53bf'), ('440232', u'\u4e73\u6e90\u7476\u65cf\u81ea\u6cbb\u53bf'), ('440233', u'\u65b0\u4e30\u53bf'), ('440281', u'\u4e50\u660c\u5e02'), ('440282', u'\u5357\u96c4\u5e02'), ('440300', u'\u6df1\u5733\u5e02'), ('440301', u'\u5e02\u8f96\u533a'), ('440303', u'\u7f57\u6e56\u533a'), ('440304', u'\u798f\u7530\u533a'), ('440305', u'\u5357\u5c71\u533a'), ('440306', u'\u5b9d\u5b89\u533a'), ('440307', u'\u9f99\u5c97\u533a'), ('440308', u'\u76d0\u7530\u533a'), ('440400', u'\u73e0\u6d77\u5e02'), ('440401', u'\u5e02\u8f96\u533a'), ('440402', u'\u9999\u6d32\u533a'), ('440403', u'\u6597\u95e8\u533a'), ('440404', u'\u91d1\u6e7e\u533a'), ('440500', u'\u6c55\u5934\u5e02'), ('440501', u'\u5e02\u8f96\u533a'), ('440507', u'\u9f99\u6e56\u533a'), ('440511', u'\u91d1\u5e73\u533a'), ('440512', u'\u6fe0\u6c5f\u533a'), ('440513', u'\u6f6e\u9633\u533a'), ('440514', u'\u6f6e\u5357\u533a'), ('440515', u'\u6f84\u6d77\u533a'), ('440523', u'\u5357\u6fb3\u53bf'), ('440600', u'\u4f5b\u5c71\u5e02'), ('440601', u'\u5e02\u8f96\u533a'), ('440604', u'\u7985\u57ce\u533a'), ('440605', u'\u5357\u6d77\u533a'), ('440606', u'\u987a\u5fb7\u533a'), ('440607', u'\u4e09\u6c34\u533a'), ('440608', u'\u9ad8\u660e\u533a'), ('440700', u'\u6c5f\u95e8\u5e02'), ('440701', u'\u5e02\u8f96\u533a'), ('440703', u'\u84ec\u6c5f\u533a'), ('440704', u'\u6c5f\u6d77\u533a'), ('440705', u'\u65b0\u4f1a\u533a'), ('440781', u'\u53f0\u5c71\u5e02'), ('440783', u'\u5f00\u5e73\u5e02'), ('440784', u'\u9e64\u5c71\u5e02'), ('440785', u'\u6069\u5e73\u5e02'), ('440800', u'\u6e5b\u6c5f\u5e02'), ('440801', u'\u5e02\u8f96\u533a'), ('440802', u'\u8d64\u574e\u533a'), ('440803', u'\u971e\u5c71\u533a'), ('440804', u'\u5761\u5934\u533a'), ('440811', u'\u9ebb\u7ae0\u533a'), ('440823', u'\u9042\u6eaa\u53bf'), ('440825', u'\u5f90\u95fb\u53bf'), ('440881', u'\u5ec9\u6c5f\u5e02'), ('440882', u'\u96f7\u5dde\u5e02'), ('440883', u'\u5434\u5ddd\u5e02'), ('440900', u'\u8302\u540d\u5e02'), ('440901', u'\u5e02\u8f96\u533a'), ('440902', u'\u8302\u5357\u533a'), ('440903', u'\u8302\u6e2f\u533a'), ('440923', u'\u7535\u767d\u53bf'), ('440981', u'\u9ad8\u5dde\u5e02'), ('440982', u'\u5316\u5dde\u5e02'), ('440983', u'\u4fe1\u5b9c\u5e02'), ('441200', u'\u8087\u5e86\u5e02'), ('441201', u'\u5e02\u8f96\u533a'), ('441202', u'\u7aef\u5dde\u533a'), ('441203', u'\u9f0e\u6e56\u533a'), ('441223', u'\u5e7f\u5b81\u53bf'), ('441224', u'\u6000\u96c6\u53bf'), ('441225', u'\u5c01\u5f00\u53bf'), ('441226', u'\u5fb7\u5e86\u53bf'), ('441283', u'\u9ad8\u8981\u5e02'), ('441284', u'\u56db\u4f1a\u5e02'), ('441300', u'\u60e0\u5dde\u5e02'), ('441301', u'\u5e02\u8f96\u533a'), ('441302', u'\u60e0\u57ce\u533a'), ('441303', u'\u60e0\u9633\u533a'), ('441322', u'\u535a\u7f57\u53bf'), ('441323', u'\u60e0\u4e1c\u53bf'), ('441324', u'\u9f99\u95e8\u53bf'), ('441400', u'\u6885\u5dde\u5e02'), ('441401', u'\u5e02\u8f96\u533a'), ('441402', u'\u6885\u6c5f\u533a'), ('441421', u'\u6885\u53bf'), ('441422', u'\u5927\u57d4\u53bf'), ('441423', u'\u4e30\u987a\u53bf'), ('441424', u'\u4e94\u534e\u53bf'), ('441426', u'\u5e73\u8fdc\u53bf'), ('441427', u'\u8549\u5cad\u53bf'), ('441481', u'\u5174\u5b81\u5e02'), ('441500', u'\u6c55\u5c3e\u5e02'), ('441501', u'\u5e02\u8f96\u533a'), ('441502', u'\u57ce\u533a'), ('441521', u'\u6d77\u4e30\u53bf'), ('441523', u'\u9646\u6cb3\u53bf'), ('441581', u'\u9646\u4e30\u5e02'), ('441600', u'\u6cb3\u6e90\u5e02'), ('441601', u'\u5e02\u8f96\u533a'), ('441602', u'\u6e90\u57ce\u533a'), ('441621', u'\u7d2b\u91d1\u53bf'), ('441622', u'\u9f99\u5ddd\u53bf'), ('441623', u'\u8fde\u5e73\u53bf'), ('441624', u'\u548c\u5e73\u53bf'), ('441625', u'\u4e1c\u6e90\u53bf'), ('441700', u'\u9633\u6c5f\u5e02'), ('441701', u'\u5e02\u8f96\u533a'), ('441702', u'\u6c5f\u57ce\u533a'), ('441721', u'\u9633\u897f\u53bf'), ('441723', u'\u9633\u4e1c\u53bf'), ('441781', u'\u9633\u6625\u5e02'), ('441800', u'\u6e05\u8fdc\u5e02'), ('441801', u'\u5e02\u8f96\u533a'), ('441802', u'\u6e05\u57ce\u533a'), ('441803', u'\u6e05\u65b0\u533a'), ('441821', u'\u4f5b\u5188\u53bf'), ('441823', u'\u9633\u5c71\u53bf'), ('441825', u'\u8fde\u5c71\u58ee\u65cf\u7476\u65cf\u81ea\u6cbb\u53bf'), ('441826', u'\u8fde\u5357\u7476\u65cf\u81ea\u6cbb\u53bf'), ('441881', u'\u82f1\u5fb7\u5e02'), ('441882', u'\u8fde\u5dde\u5e02'), ('441900', u'\u4e1c\u839e\u5e02'), ('442000', u'\u4e2d\u5c71\u5e02'), ('445100', u'\u6f6e\u5dde\u5e02'), ('445101', u'\u5e02\u8f96\u533a'), ('445102', u'\u6e58\u6865\u533a'), ('445103', u'\u6f6e\u5b89\u533a'), ('445122', u'\u9976\u5e73\u53bf'), ('445200', u'\u63ed\u9633\u5e02'), ('445201', u'\u5e02\u8f96\u533a'), ('445202', u'\u6995\u57ce\u533a'), ('445203', u'\u63ed\u4e1c\u533a'), ('445222', u'\u63ed\u897f\u53bf'), ('445224', u'\u60e0\u6765\u53bf'), ('445281', u'\u666e\u5b81\u5e02'), ('445300', u'\u4e91\u6d6e\u5e02'), ('445301', u'\u5e02\u8f96\u533a'), ('445302', u'\u4e91\u57ce\u533a'), ('445321', u'\u65b0\u5174\u53bf'), ('445322', u'\u90c1\u5357\u53bf'), ('445323', u'\u4e91\u5b89\u53bf'), ('445381', u'\u7f57\u5b9a\u5e02'), ('450000', u'\u5e7f\u897f\u58ee\u65cf\u81ea\u6cbb\u533a'), ('450100', u'\u5357\u5b81\u5e02'), ('450101', u'\u5e02\u8f96\u533a'), ('450102', u'\u5174\u5b81\u533a'), ('450103', u'\u9752\u79c0\u533a'), ('450105', u'\u6c5f\u5357\u533a'), ('450107', u'\u897f\u4e61\u5858\u533a'), ('450108', u'\u826f\u5e86\u533a'), ('450109', u'\u9095\u5b81\u533a'), ('450122', u'\u6b66\u9e23\u53bf'), ('450123', u'\u9686\u5b89\u53bf'), ('450124', u'\u9a6c\u5c71\u53bf'), ('450125', u'\u4e0a\u6797\u53bf'), ('450126', u'\u5bbe\u9633\u53bf'), ('450127', u'\u6a2a\u53bf'), ('450200', u'\u67f3\u5dde\u5e02'), ('450201', u'\u5e02\u8f96\u533a'), ('450202', u'\u57ce\u4e2d\u533a'), ('450203', u'\u9c7c\u5cf0\u533a'), ('450204', u'\u67f3\u5357\u533a'), ('450205', u'\u67f3\u5317\u533a'), ('450221', u'\u67f3\u6c5f\u53bf'), ('450222', u'\u67f3\u57ce\u53bf'), ('450223', u'\u9e7f\u5be8\u53bf'), ('450224', u'\u878d\u5b89\u53bf'), ('450225', u'\u878d\u6c34\u82d7\u65cf\u81ea\u6cbb\u53bf'), ('450226', u'\u4e09\u6c5f\u4f97\u65cf\u81ea\u6cbb\u53bf'), ('450300', u'\u6842\u6797\u5e02'), ('450301', u'\u5e02\u8f96\u533a'), ('450302', u'\u79c0\u5cf0\u533a'), ('450303', u'\u53e0\u5f69\u533a'), ('450304', u'\u8c61\u5c71\u533a'), ('450305', u'\u4e03\u661f\u533a'), ('450311', u'\u96c1\u5c71\u533a'), ('450312', u'\u4e34\u6842\u533a'), ('450321', u'\u9633\u6714\u53bf'), ('450323', u'\u7075\u5ddd\u53bf'), ('450324', u'\u5168\u5dde\u53bf'), ('450325', u'\u5174\u5b89\u53bf'), ('450326', u'\u6c38\u798f\u53bf'), ('450327', u'\u704c\u9633\u53bf'), ('450328', u'\u9f99\u80dc\u5404\u65cf\u81ea\u6cbb\u53bf'), ('450329', u'\u8d44\u6e90\u53bf'), ('450330', u'\u5e73\u4e50\u53bf'), ('450331', u'\u8354\u6d66\u53bf'), ('450332', u'\u606d\u57ce\u7476\u65cf\u81ea\u6cbb\u53bf'), ('450400', u'\u68a7\u5dde\u5e02'), ('450401', u'\u5e02\u8f96\u533a'), ('450403', u'\u4e07\u79c0\u533a'), ('450405', u'\u957f\u6d32\u533a'), ('450406', u'\u9f99\u5729\u533a'), ('450421', u'\u82cd\u68a7\u53bf'), ('450422', u'\u85e4\u53bf'), ('450423', u'\u8499\u5c71\u53bf'), ('450481', u'\u5c91\u6eaa\u5e02'), ('450500', u'\u5317\u6d77\u5e02'), ('450501', u'\u5e02\u8f96\u533a'), ('450502', u'\u6d77\u57ce\u533a'), ('450503', u'\u94f6\u6d77\u533a'), ('450512', u'\u94c1\u5c71\u6e2f\u533a'), ('450521', u'\u5408\u6d66\u53bf'), ('450600', u'\u9632\u57ce\u6e2f\u5e02'), ('450601', u'\u5e02\u8f96\u533a'), ('450602', u'\u6e2f\u53e3\u533a'), ('450603', u'\u9632\u57ce\u533a'), ('450621', u'\u4e0a\u601d\u53bf'), ('450681', u'\u4e1c\u5174\u5e02'), ('450700', u'\u94a6\u5dde\u5e02'), ('450701', u'\u5e02\u8f96\u533a'), ('450702', u'\u94a6\u5357\u533a'), ('450703', u'\u94a6\u5317\u533a'), ('450721', u'\u7075\u5c71\u53bf'), ('450722', u'\u6d66\u5317\u53bf'), ('450800', u'\u8d35\u6e2f\u5e02'), ('450801', u'\u5e02\u8f96\u533a'), ('450802', u'\u6e2f\u5317\u533a'), ('450803', u'\u6e2f\u5357\u533a'), ('450804', u'\u8983\u5858\u533a'), ('450821', u'\u5e73\u5357\u53bf'), ('450881', u'\u6842\u5e73\u5e02'), ('450900', u'\u7389\u6797\u5e02'), ('450901', u'\u5e02\u8f96\u533a'), ('450902', u'\u7389\u5dde\u533a'), ('450903', u'\u798f\u7ef5\u533a'), ('450921', u'\u5bb9\u53bf'), ('450922', u'\u9646\u5ddd\u53bf'), ('450923', u'\u535a\u767d\u53bf'), ('450924', u'\u5174\u4e1a\u53bf'), ('450981', u'\u5317\u6d41\u5e02'), ('451000', u'\u767e\u8272\u5e02'), ('451001', u'\u5e02\u8f96\u533a'), ('451002', u'\u53f3\u6c5f\u533a'), ('451021', u'\u7530\u9633\u53bf'), ('451022', u'\u7530\u4e1c\u53bf'), ('451023', u'\u5e73\u679c\u53bf'), ('451024', u'\u5fb7\u4fdd\u53bf'), ('451025', u'\u9756\u897f\u53bf'), ('451026', u'\u90a3\u5761\u53bf'), ('451027', u'\u51cc\u4e91\u53bf'), ('451028', u'\u4e50\u4e1a\u53bf'), ('451029', u'\u7530\u6797\u53bf'), ('451030', u'\u897f\u6797\u53bf'), ('451031', u'\u9686\u6797\u5404\u65cf\u81ea\u6cbb\u53bf'), ('451100', u'\u8d3a\u5dde\u5e02'), ('451101', u'\u5e02\u8f96\u533a'), ('451102', u'\u516b\u6b65\u533a'), ('451121', u'\u662d\u5e73\u53bf'), ('451122', u'\u949f\u5c71\u53bf'), ('451123', u'\u5bcc\u5ddd\u7476\u65cf\u81ea\u6cbb\u53bf'), ('451200', u'\u6cb3\u6c60\u5e02'), ('451201', u'\u5e02\u8f96\u533a'), ('451202', u'\u91d1\u57ce\u6c5f\u533a'), ('451221', u'\u5357\u4e39\u53bf'), ('451222', u'\u5929\u5ce8\u53bf'), ('451223', u'\u51e4\u5c71\u53bf'), ('451224', u'\u4e1c\u5170\u53bf'), ('451225', u'\u7f57\u57ce\u4eeb\u4f6c\u65cf\u81ea\u6cbb\u53bf'), ('451226', u'\u73af\u6c5f\u6bdb\u5357\u65cf\u81ea\u6cbb\u53bf'), ('451227', u'\u5df4\u9a6c\u7476\u65cf\u81ea\u6cbb\u53bf'), ('451228', u'\u90fd\u5b89\u7476\u65cf\u81ea\u6cbb\u53bf'), ('451229', u'\u5927\u5316\u7476\u65cf\u81ea\u6cbb\u53bf'), ('451281', u'\u5b9c\u5dde\u5e02'), ('451300', u'\u6765\u5bbe\u5e02'), ('451301', u'\u5e02\u8f96\u533a'), ('451302', u'\u5174\u5bbe\u533a'), ('451321', u'\u5ffb\u57ce\u53bf'), ('451322', u'\u8c61\u5dde\u53bf'), ('451323', u'\u6b66\u5ba3\u53bf'), ('451324', u'\u91d1\u79c0\u7476\u65cf\u81ea\u6cbb\u53bf'), ('451381', u'\u5408\u5c71\u5e02'), ('451400', u'\u5d07\u5de6\u5e02'), ('451401', u'\u5e02\u8f96\u533a'), ('451402', u'\u6c5f\u5dde\u533a'), ('451421', u'\u6276\u7ee5\u53bf'), ('451422', u'\u5b81\u660e\u53bf'), ('451423', u'\u9f99\u5dde\u53bf'), ('451424', u'\u5927\u65b0\u53bf'), ('451425', u'\u5929\u7b49\u53bf'), ('451481', u'\u51ed\u7965\u5e02'), ('460000', u'\u6d77\u5357\u7701'), ('460100', u'\u6d77\u53e3\u5e02'), ('460101', u'\u5e02\u8f96\u533a'), ('460105', u'\u79c0\u82f1\u533a'), ('460106', u'\u9f99\u534e\u533a'), ('460107', u'\u743c\u5c71\u533a'), ('460108', u'\u7f8e\u5170\u533a'), ('460200', u'\u4e09\u4e9a\u5e02'), ('460201', u'\u5e02\u8f96\u533a'), ('460300', u'\u4e09\u6c99\u5e02'), ('460321', u'\u897f\u6c99\u7fa4\u5c9b'), ('460322', u'\u5357\u6c99\u7fa4\u5c9b'), ('460323', u'\u4e2d\u6c99\u7fa4\u5c9b\u7684\u5c9b\u7901\u53ca\u5176\u6d77\u57df'), ('469000', u'\u7701\u76f4\u8f96\u53bf\u7ea7\u884c\u653f\u533a\u5212'), ('469001', u'\u4e94\u6307\u5c71\u5e02'), ('469002', u'\u743c\u6d77\u5e02'), ('469003', u'\u510b\u5dde\u5e02'), ('469005', u'\u6587\u660c\u5e02'), ('469006', u'\u4e07\u5b81\u5e02'), ('469007', u'\u4e1c\u65b9\u5e02'), ('469021', u'\u5b9a\u5b89\u53bf'), ('469022', u'\u5c6f\u660c\u53bf'), ('469023', u'\u6f84\u8fc8\u53bf'), ('469024', u'\u4e34\u9ad8\u53bf'), ('469025', u'\u767d\u6c99\u9ece\u65cf\u81ea\u6cbb\u53bf'), ('469026', u'\u660c\u6c5f\u9ece\u65cf\u81ea\u6cbb\u53bf'), ('469027', u'\u4e50\u4e1c\u9ece\u65cf\u81ea\u6cbb\u53bf'), ('469028', u'\u9675\u6c34\u9ece\u65cf\u81ea\u6cbb\u53bf'), ('469029', u'\u4fdd\u4ead\u9ece\u65cf\u82d7\u65cf\u81ea\u6cbb\u53bf'), ('469030', u'\u743c\u4e2d\u9ece\u65cf\u82d7\u65cf\u81ea\u6cbb\u53bf'), ('500000', u'\u91cd\u5e86\u5e02'), ('500100', u'\u5e02\u8f96\u533a'), ('500101', u'\u4e07\u5dde\u533a'), ('500102', u'\u6daa\u9675\u533a'), ('500103', u'\u6e1d\u4e2d\u533a'), ('500104', u'\u5927\u6e21\u53e3\u533a'), ('500105', u'\u6c5f\u5317\u533a'), ('500106', u'\u6c99\u576a\u575d\u533a'), ('500107', u'\u4e5d\u9f99\u5761\u533a'), ('500108', u'\u5357\u5cb8\u533a'), ('500109', u'\u5317\u789a\u533a'), ('500110', u'\u7da6\u6c5f\u533a'), ('500111', u'\u5927\u8db3\u533a'), ('500112', u'\u6e1d\u5317\u533a'), ('500113', u'\u5df4\u5357\u533a'), ('500114', u'\u9ed4\u6c5f\u533a'), ('500115', u'\u957f\u5bff\u533a'), ('500116', u'\u6c5f\u6d25\u533a'), ('500117', u'\u5408\u5ddd\u533a'), ('500118', u'\u6c38\u5ddd\u533a'), ('500119', u'\u5357\u5ddd\u533a'), ('500200', u'\u53bf'), ('500223', u'\u6f7c\u5357\u53bf'), ('500224', u'\u94dc\u6881\u53bf'), ('500226', u'\u8363\u660c\u53bf'), ('500227', u'\u74a7\u5c71\u53bf'), ('500228', u'\u6881\u5e73\u53bf'), ('500229', u'\u57ce\u53e3\u53bf'), ('500230', u'\u4e30\u90fd\u53bf'), ('500231', u'\u57ab\u6c5f\u53bf'), ('500232', u'\u6b66\u9686\u53bf'), ('500233', u'\u5fe0\u53bf'), ('500234', u'\u5f00\u53bf'), ('500235', u'\u4e91\u9633\u53bf'), ('500236', u'\u5949\u8282\u53bf'), ('500237', u'\u5deb\u5c71\u53bf'), ('500238', u'\u5deb\u6eaa\u53bf'), ('500240', u'\u77f3\u67f1\u571f\u5bb6\u65cf\u81ea\u6cbb\u53bf'), ('500241', u'\u79c0\u5c71\u571f\u5bb6\u65cf\u82d7\u65cf\u81ea\u6cbb\u53bf'), ('500242', u'\u9149\u9633\u571f\u5bb6\u65cf\u82d7\u65cf\u81ea\u6cbb\u53bf'), ('500243', u'\u5f6d\u6c34\u82d7\u65cf\u571f\u5bb6\u65cf\u81ea\u6cbb\u53bf'), ('510000', u'\u56db\u5ddd\u7701'), ('510100', u'\u6210\u90fd\u5e02'), ('510101', u'\u5e02\u8f96\u533a'), ('510104', u'\u9526\u6c5f\u533a'), ('510105', u'\u9752\u7f8a\u533a'), ('510106', u'\u91d1\u725b\u533a'), ('510107', u'\u6b66\u4faf\u533a'), ('510108', u'\u6210\u534e\u533a'), ('510112', u'\u9f99\u6cc9\u9a7f\u533a'), ('510113', u'\u9752\u767d\u6c5f\u533a'), ('510114', u'\u65b0\u90fd\u533a'), ('510115', u'\u6e29\u6c5f\u533a'), ('510121', u'\u91d1\u5802\u53bf'), ('510122', u'\u53cc\u6d41\u53bf'), ('510124', u'\u90eb\u53bf'), ('510129', u'\u5927\u9091\u53bf'), ('510131', u'\u84b2\u6c5f\u53bf'), ('510132', u'\u65b0\u6d25\u53bf'), ('510181', u'\u90fd\u6c5f\u5830\u5e02'), ('510182', u'\u5f6d\u5dde\u5e02'), ('510183', u'\u909b\u5d03\u5e02'), ('510184', u'\u5d07\u5dde\u5e02'), ('510300', u'\u81ea\u8d21\u5e02'), ('510301', u'\u5e02\u8f96\u533a'), ('510302', u'\u81ea\u6d41\u4e95\u533a'), ('510303', u'\u8d21\u4e95\u533a'), ('510304', u'\u5927\u5b89\u533a'), ('510311', u'\u6cbf\u6ee9\u533a'), ('510321', u'\u8363\u53bf'), ('510322', u'\u5bcc\u987a\u53bf'), ('510400', u'\u6500\u679d\u82b1\u5e02'), ('510401', u'\u5e02\u8f96\u533a'), ('510402', u'\u4e1c\u533a'), ('510403', u'\u897f\u533a'), ('510411', u'\u4ec1\u548c\u533a'), ('510421', u'\u7c73\u6613\u53bf'), ('510422', u'\u76d0\u8fb9\u53bf'), ('510500', u'\u6cf8\u5dde\u5e02'), ('510501', u'\u5e02\u8f96\u533a'), ('510502', u'\u6c5f\u9633\u533a'), ('510503', u'\u7eb3\u6eaa\u533a'), ('510504', u'\u9f99\u9a6c\u6f6d\u533a'), ('510521', u'\u6cf8\u53bf'), ('510522', u'\u5408\u6c5f\u53bf'), ('510524', u'\u53d9\u6c38\u53bf'), ('510525', u'\u53e4\u853a\u53bf'), ('510600', u'\u5fb7\u9633\u5e02'), ('510601', u'\u5e02\u8f96\u533a'), ('510603', u'\u65cc\u9633\u533a'), ('510623', u'\u4e2d\u6c5f\u53bf'), ('510626', u'\u7f57\u6c5f\u53bf'), ('510681', u'\u5e7f\u6c49\u5e02'), ('510682', u'\u4ec0\u90a1\u5e02'), ('510683', u'\u7ef5\u7af9\u5e02'), ('510700', u'\u7ef5\u9633\u5e02'), ('510701', u'\u5e02\u8f96\u533a'), ('510703', u'\u6daa\u57ce\u533a'), ('510704', u'\u6e38\u4ed9\u533a'), ('510722', u'\u4e09\u53f0\u53bf'), ('510723', u'\u76d0\u4ead\u53bf'), ('510724', u'\u5b89\u53bf'), ('510725', u'\u6893\u6f7c\u53bf'), ('510726', u'\u5317\u5ddd\u7f8c\u65cf\u81ea\u6cbb\u53bf'), ('510727', u'\u5e73\u6b66\u53bf'), ('510781', u'\u6c5f\u6cb9\u5e02'), ('510800', u'\u5e7f\u5143\u5e02'), ('510801', u'\u5e02\u8f96\u533a'), ('510802', u'\u5229\u5dde\u533a'), ('510811', u'\u5143\u575d\u533a'), ('510812', u'\u671d\u5929\u533a'), ('510821', u'\u65fa\u82cd\u53bf'), ('510822', u'\u9752\u5ddd\u53bf'), ('510823', u'\u5251\u9601\u53bf'), ('510824', u'\u82cd\u6eaa\u53bf'), ('510900', u'\u9042\u5b81\u5e02'), ('510901', u'\u5e02\u8f96\u533a'), ('510903', u'\u8239\u5c71\u533a'), ('510904', u'\u5b89\u5c45\u533a'), ('510921', u'\u84ec\u6eaa\u53bf'), ('510922', u'\u5c04\u6d2a\u53bf'), ('510923', u'\u5927\u82f1\u53bf'), ('511000', u'\u5185\u6c5f\u5e02'), ('511001', u'\u5e02\u8f96\u533a'), ('511002', u'\u5e02\u4e2d\u533a'), ('511011', u'\u4e1c\u5174\u533a'), ('511024', u'\u5a01\u8fdc\u53bf'), ('511025', u'\u8d44\u4e2d\u53bf'), ('511028', u'\u9686\u660c\u53bf'), ('511100', u'\u4e50\u5c71\u5e02'), ('511101', u'\u5e02\u8f96\u533a'), ('511102', u'\u5e02\u4e2d\u533a'), ('511111', u'\u6c99\u6e7e\u533a'), ('511112', u'\u4e94\u901a\u6865\u533a'), ('511113', u'\u91d1\u53e3\u6cb3\u533a'), ('511123', u'\u728d\u4e3a\u53bf'), ('511124', u'\u4e95\u7814\u53bf'), ('511126', u'\u5939\u6c5f\u53bf'), ('511129', u'\u6c90\u5ddd\u53bf'), ('511132', u'\u5ce8\u8fb9\u5f5d\u65cf\u81ea\u6cbb\u53bf'), ('511133', u'\u9a6c\u8fb9\u5f5d\u65cf\u81ea\u6cbb\u53bf'), ('511181', u'\u5ce8\u7709\u5c71\u5e02'), ('511300', u'\u5357\u5145\u5e02'), ('511301', u'\u5e02\u8f96\u533a'), ('511302', u'\u987a\u5e86\u533a'), ('511303', u'\u9ad8\u576a\u533a'), ('511304', u'\u5609\u9675\u533a'), ('511321', u'\u5357\u90e8\u53bf'), ('511322', u'\u8425\u5c71\u53bf'), ('511323', u'\u84ec\u5b89\u53bf'), ('511324', u'\u4eea\u9647\u53bf'), ('511325', u'\u897f\u5145\u53bf'), ('511381', u'\u9606\u4e2d\u5e02'), ('511400', u'\u7709\u5c71\u5e02'), ('511401', u'\u5e02\u8f96\u533a'), ('511402', u'\u4e1c\u5761\u533a'), ('511421', u'\u4ec1\u5bff\u53bf'), ('511422', u'\u5f6d\u5c71\u53bf'), ('511423', u'\u6d2a\u96c5\u53bf'), ('511424', u'\u4e39\u68f1\u53bf'), ('511425', u'\u9752\u795e\u53bf'), ('511500', u'\u5b9c\u5bbe\u5e02'), ('511501', u'\u5e02\u8f96\u533a'), ('511502', u'\u7fe0\u5c4f\u533a'), ('511503', u'\u5357\u6eaa\u533a'), ('511521', u'\u5b9c\u5bbe\u53bf'), ('511523', u'\u6c5f\u5b89\u53bf'), ('511524', u'\u957f\u5b81\u53bf'), ('511525', u'\u9ad8\u53bf'), ('511526', u'\u73d9\u53bf'), ('511527', u'\u7b60\u8fde\u53bf'), ('511528', u'\u5174\u6587\u53bf'), ('511529', u'\u5c4f\u5c71\u53bf'), ('511600', u'\u5e7f\u5b89\u5e02'), ('511601', u'\u5e02\u8f96\u533a'), ('511602', u'\u5e7f\u5b89\u533a'), ('511603', u'\u524d\u950b\u533a'), ('511621', u'\u5cb3\u6c60\u53bf'), ('511622', u'\u6b66\u80dc\u53bf'), ('511623', u'\u90bb\u6c34\u53bf'), ('511681', u'\u534e\u84e5\u5e02'), ('511700', u'\u8fbe\u5dde\u5e02'), ('511701', u'\u5e02\u8f96\u533a'), ('511702', u'\u901a\u5ddd\u533a'), ('511703', u'\u8fbe\u5ddd\u533a'), ('511722', u'\u5ba3\u6c49\u53bf'), ('511723', u'\u5f00\u6c5f\u53bf'), ('511724', u'\u5927\u7af9\u53bf'), ('511725', u'\u6e20\u53bf'), ('511781', u'\u4e07\u6e90\u5e02'), ('511800', u'\u96c5\u5b89\u5e02'), ('511801', u'\u5e02\u8f96\u533a'), ('511802', u'\u96e8\u57ce\u533a'), ('511803', u'\u540d\u5c71\u533a'), ('511822', u'\u8365\u7ecf\u53bf'), ('511823', u'\u6c49\u6e90\u53bf'), ('511824', u'\u77f3\u68c9\u53bf'), ('511825', u'\u5929\u5168\u53bf'), ('511826', u'\u82a6\u5c71\u53bf'), ('511827', u'\u5b9d\u5174\u53bf'), ('511900', u'\u5df4\u4e2d\u5e02'), ('511901', u'\u5e02\u8f96\u533a'), ('511902', u'\u5df4\u5dde\u533a'), ('511903', u'\u6069\u9633\u533a'), ('511921', u'\u901a\u6c5f\u53bf'), ('511922', u'\u5357\u6c5f\u53bf'), ('511923', u'\u5e73\u660c\u53bf'), ('512000', u'\u8d44\u9633\u5e02'), ('512001', u'\u5e02\u8f96\u533a'), ('512002', u'\u96c1\u6c5f\u533a'), ('512021', u'\u5b89\u5cb3\u53bf'), ('512022', u'\u4e50\u81f3\u53bf'), ('512081', u'\u7b80\u9633\u5e02'), ('513200', u'\u963f\u575d\u85cf\u65cf\u7f8c\u65cf\u81ea\u6cbb\u5dde'), ('513221', u'\u6c76\u5ddd\u53bf'), ('513222', u'\u7406\u53bf'), ('513223', u'\u8302\u53bf'), ('513224', u'\u677e\u6f58\u53bf'), ('513225', u'\u4e5d\u5be8\u6c9f\u53bf'), ('513226', u'\u91d1\u5ddd\u53bf'), ('513227', u'\u5c0f\u91d1\u53bf'), ('513228', u'\u9ed1\u6c34\u53bf'), ('513229', u'\u9a6c\u5c14\u5eb7\u53bf'), ('513230', u'\u58e4\u5858\u53bf'), ('513231', u'\u963f\u575d\u53bf'), ('513232', u'\u82e5\u5c14\u76d6\u53bf'), ('513233', u'\u7ea2\u539f\u53bf'), ('513300', u'\u7518\u5b5c\u85cf\u65cf\u81ea\u6cbb\u5dde'), ('513321', u'\u5eb7\u5b9a\u53bf'), ('513322', u'\u6cf8\u5b9a\u53bf'), ('513323', u'\u4e39\u5df4\u53bf'), ('513324', u'\u4e5d\u9f99\u53bf'), ('513325', u'\u96c5\u6c5f\u53bf'), ('513326', u'\u9053\u5b5a\u53bf'), ('513327', u'\u7089\u970d\u53bf'), ('513328', u'\u7518\u5b5c\u53bf'), ('513329', u'\u65b0\u9f99\u53bf'), ('513330', u'\u5fb7\u683c\u53bf'), ('513331', u'\u767d\u7389\u53bf'), ('513332', u'\u77f3\u6e20\u53bf'), ('513333', u'\u8272\u8fbe\u53bf'), ('513334', u'\u7406\u5858\u53bf'), ('513335', u'\u5df4\u5858\u53bf'), ('513336', u'\u4e61\u57ce\u53bf'), ('513337', u'\u7a3b\u57ce\u53bf'), ('513338', u'\u5f97\u8363\u53bf'), ('513400', u'\u51c9\u5c71\u5f5d\u65cf\u81ea\u6cbb\u5dde'), ('513401', u'\u897f\u660c\u5e02'), ('513422', u'\u6728\u91cc\u85cf\u65cf\u81ea\u6cbb\u53bf'), ('513423', u'\u76d0\u6e90\u53bf'), ('513424', u'\u5fb7\u660c\u53bf'), ('513425', u'\u4f1a\u7406\u53bf'), ('513426', u'\u4f1a\u4e1c\u53bf'), ('513427', u'\u5b81\u5357\u53bf'), ('513428', u'\u666e\u683c\u53bf'), ('513429', u'\u5e03\u62d6\u53bf'), ('513430', u'\u91d1\u9633\u53bf'), ('513431', u'\u662d\u89c9\u53bf'), ('513432', u'\u559c\u5fb7\u53bf'), ('513433', u'\u5195\u5b81\u53bf'), ('513434', u'\u8d8a\u897f\u53bf'), ('513435', u'\u7518\u6d1b\u53bf'), ('513436', u'\u7f8e\u59d1\u53bf'), ('513437', u'\u96f7\u6ce2\u53bf'), ('520000', u'\u8d35\u5dde\u7701'), ('520100', u'\u8d35\u9633\u5e02'), ('520101', u'\u5e02\u8f96\u533a'), ('520102', u'\u5357\u660e\u533a'), ('520103', u'\u4e91\u5ca9\u533a'), ('520111', u'\u82b1\u6eaa\u533a'), ('520112', u'\u4e4c\u5f53\u533a'), ('520113', u'\u767d\u4e91\u533a'), ('520115', u'\u89c2\u5c71\u6e56\u533a'), ('520121', u'\u5f00\u9633\u53bf'), ('520122', u'\u606f\u70fd\u53bf'), ('520123', u'\u4fee\u6587\u53bf'), ('520181', u'\u6e05\u9547\u5e02'), ('520200', u'\u516d\u76d8\u6c34\u5e02'), ('520201', u'\u949f\u5c71\u533a'), ('520203', u'\u516d\u679d\u7279\u533a'), ('520221', u'\u6c34\u57ce\u53bf'), ('520222', u'\u76d8\u53bf'), ('520300', u'\u9075\u4e49\u5e02'), ('520301', u'\u5e02\u8f96\u533a'), ('520302', u'\u7ea2\u82b1\u5c97\u533a'), ('520303', u'\u6c47\u5ddd\u533a'), ('520321', u'\u9075\u4e49\u53bf'), ('520322', u'\u6850\u6893\u53bf'), ('520323', u'\u7ee5\u9633\u53bf'), ('520324', u'\u6b63\u5b89\u53bf'), ('520325', u'\u9053\u771f\u4ee1\u4f6c\u65cf\u82d7\u65cf\u81ea\u6cbb\u53bf'), ('520326', u'\u52a1\u5ddd\u4ee1\u4f6c\u65cf\u82d7\u65cf\u81ea\u6cbb\u53bf'), ('520327', u'\u51e4\u5188\u53bf'), ('520328', u'\u6e44\u6f6d\u53bf'), ('520329', u'\u4f59\u5e86\u53bf'), ('520330', u'\u4e60\u6c34\u53bf'), ('520381', u'\u8d64\u6c34\u5e02'), ('520382', u'\u4ec1\u6000\u5e02'), ('520400', u'\u5b89\u987a\u5e02'), ('520401', u'\u5e02\u8f96\u533a'), ('520402', u'\u897f\u79c0\u533a'), ('520421', u'\u5e73\u575d\u53bf'), ('520422', u'\u666e\u5b9a\u53bf'), ('520423', u'\u9547\u5b81\u5e03\u4f9d\u65cf\u82d7\u65cf\u81ea\u6cbb\u53bf'), ('520424', u'\u5173\u5cad\u5e03\u4f9d\u65cf\u82d7\u65cf\u81ea\u6cbb\u53bf'), ('520425', u'\u7d2b\u4e91\u82d7\u65cf\u5e03\u4f9d\u65cf\u81ea\u6cbb\u53bf'), ('520500', u'\u6bd5\u8282\u5e02'), ('520501', u'\u5e02\u8f96\u533a'), ('520502', u'\u4e03\u661f\u5173\u533a'), ('520521', u'\u5927\u65b9\u53bf'), ('520522', u'\u9ed4\u897f\u53bf'), ('520523', u'\u91d1\u6c99\u53bf'), ('520524', u'\u7ec7\u91d1\u53bf'), ('520525', u'\u7eb3\u96cd\u53bf'), ('520526', u'\u5a01\u5b81\u5f5d\u65cf\u56de\u65cf\u82d7\u65cf\u81ea\u6cbb\u53bf'), ('520527', u'\u8d6b\u7ae0\u53bf'), ('520600', u'\u94dc\u4ec1\u5e02'), ('520601', u'\u5e02\u8f96\u533a'), ('520602', u'\u78a7\u6c5f\u533a'), ('520603', u'\u4e07\u5c71\u533a'), ('520621', u'\u6c5f\u53e3\u53bf'), ('520622', u'\u7389\u5c4f\u4f97\u65cf\u81ea\u6cbb\u53bf'), ('520623', u'\u77f3\u9621\u53bf'), ('520624', u'\u601d\u5357\u53bf'), ('520625', u'\u5370\u6c5f\u571f\u5bb6\u65cf\u82d7\u65cf\u81ea\u6cbb\u53bf'), ('520626', u'\u5fb7\u6c5f\u53bf'), ('520627', u'\u6cbf\u6cb3\u571f\u5bb6\u65cf\u81ea\u6cbb\u53bf'), ('520628', u'\u677e\u6843\u82d7\u65cf\u81ea\u6cbb\u53bf'), ('522300', u'\u9ed4\u897f\u5357\u5e03\u4f9d\u65cf\u82d7\u65cf\u81ea\u6cbb\u5dde'), ('522301', u'\u5174\u4e49\u5e02'), ('522322', u'\u5174\u4ec1\u53bf'), ('522323', u'\u666e\u5b89\u53bf'), ('522324', u'\u6674\u9686\u53bf'), ('522325', u'\u8d1e\u4e30\u53bf'), ('522326', u'\u671b\u8c1f\u53bf'), ('522327', u'\u518c\u4ea8\u53bf'), ('522328', u'\u5b89\u9f99\u53bf'), ('522600', u'\u9ed4\u4e1c\u5357\u82d7\u65cf\u4f97\u65cf\u81ea\u6cbb\u5dde'), ('522601', u'\u51ef\u91cc\u5e02'), ('522622', u'\u9ec4\u5e73\u53bf'), ('522623', u'\u65bd\u79c9\u53bf'), ('522624', u'\u4e09\u7a57\u53bf'), ('522625', u'\u9547\u8fdc\u53bf'), ('522626', u'\u5c91\u5de9\u53bf'), ('522627', u'\u5929\u67f1\u53bf'), ('522628', u'\u9526\u5c4f\u53bf'), ('522629', u'\u5251\u6cb3\u53bf'), ('522630', u'\u53f0\u6c5f\u53bf'), ('522631', u'\u9ece\u5e73\u53bf'), ('522632', u'\u6995\u6c5f\u53bf'), ('522633', u'\u4ece\u6c5f\u53bf'), ('522634', u'\u96f7\u5c71\u53bf'), ('522635', u'\u9ebb\u6c5f\u53bf'), ('522636', u'\u4e39\u5be8\u53bf'), ('522700', u'\u9ed4\u5357\u5e03\u4f9d\u65cf\u82d7\u65cf\u81ea\u6cbb\u5dde'), ('522701', u'\u90fd\u5300\u5e02'), ('522702', u'\u798f\u6cc9\u5e02'), ('522722', u'\u8354\u6ce2\u53bf'), ('522723', u'\u8d35\u5b9a\u53bf'), ('522725', u'\u74ee\u5b89\u53bf'), ('522726', u'\u72ec\u5c71\u53bf'), ('522727', u'\u5e73\u5858\u53bf'), ('522728', u'\u7f57\u7538\u53bf'), ('522729', u'\u957f\u987a\u53bf'), ('522730', u'\u9f99\u91cc\u53bf'), ('522731', u'\u60e0\u6c34\u53bf'), ('522732', u'\u4e09\u90fd\u6c34\u65cf\u81ea\u6cbb\u53bf'), ('530000', u'\u4e91\u5357\u7701'), ('530100', u'\u6606\u660e\u5e02'), ('530101', u'\u5e02\u8f96\u533a'), ('530102', u'\u4e94\u534e\u533a'), ('530103', u'\u76d8\u9f99\u533a'), ('530111', u'\u5b98\u6e21\u533a'), ('530112', u'\u897f\u5c71\u533a'), ('530113', u'\u4e1c\u5ddd\u533a'), ('530114', u'\u5448\u8d21\u533a'), ('530122', u'\u664b\u5b81\u53bf'), ('530124', u'\u5bcc\u6c11\u53bf'), ('530125', u'\u5b9c\u826f\u53bf'), ('530126', u'\u77f3\u6797\u5f5d\u65cf\u81ea\u6cbb\u53bf'), ('530127', u'\u5d69\u660e\u53bf'), ('530128', u'\u7984\u529d\u5f5d\u65cf\u82d7\u65cf\u81ea\u6cbb\u53bf'), ('530129', u'\u5bfb\u7538\u56de\u65cf\u5f5d\u65cf\u81ea\u6cbb\u53bf'), ('530181', u'\u5b89\u5b81\u5e02'), ('530300', u'\u66f2\u9756\u5e02'), ('530301', u'\u5e02\u8f96\u533a'), ('530302', u'\u9e92\u9e9f\u533a'), ('530321', u'\u9a6c\u9f99\u53bf'), ('530322', u'\u9646\u826f\u53bf'), ('530323', u'\u5e08\u5b97\u53bf'), ('530324', u'\u7f57\u5e73\u53bf'), ('530325', u'\u5bcc\u6e90\u53bf'), ('530326', u'\u4f1a\u6cfd\u53bf'), ('530328', u'\u6cbe\u76ca\u53bf'), ('530381', u'\u5ba3\u5a01\u5e02'), ('530400', u'\u7389\u6eaa\u5e02'), ('530401', u'\u5e02\u8f96\u533a'), ('530402', u'\u7ea2\u5854\u533a'), ('530421', u'\u6c5f\u5ddd\u53bf'), ('530422', u'\u6f84\u6c5f\u53bf'), ('530423', u'\u901a\u6d77\u53bf'), ('530424', u'\u534e\u5b81\u53bf'), ('530425', u'\u6613\u95e8\u53bf'), ('530426', u'\u5ce8\u5c71\u5f5d\u65cf\u81ea\u6cbb\u53bf'), ('530427', u'\u65b0\u5e73\u5f5d\u65cf\u50a3\u65cf\u81ea\u6cbb\u53bf'), ('530428', u'\u5143\u6c5f\u54c8\u5c3c\u65cf\u5f5d\u65cf\u50a3\u65cf\u81ea\u6cbb\u53bf'), ('530500', u'\u4fdd\u5c71\u5e02'), ('530501', u'\u5e02\u8f96\u533a'), ('530502', u'\u9686\u9633\u533a'), ('530521', u'\u65bd\u7538\u53bf'), ('530522', u'\u817e\u51b2\u53bf'), ('530523', u'\u9f99\u9675\u53bf'), ('530524', u'\u660c\u5b81\u53bf'), ('530600', u'\u662d\u901a\u5e02'), ('530601', u'\u5e02\u8f96\u533a'), ('530602', u'\u662d\u9633\u533a'), ('530621', u'\u9c81\u7538\u53bf'), ('530622', u'\u5de7\u5bb6\u53bf'), ('530623', u'\u76d0\u6d25\u53bf'), ('530624', u'\u5927\u5173\u53bf'), ('530625', u'\u6c38\u5584\u53bf'), ('530626', u'\u7ee5\u6c5f\u53bf'), ('530627', u'\u9547\u96c4\u53bf'), ('530628', u'\u5f5d\u826f\u53bf'), ('530629', u'\u5a01\u4fe1\u53bf'), ('530630', u'\u6c34\u5bcc\u53bf'), ('530700', u'\u4e3d\u6c5f\u5e02'), ('530701', u'\u5e02\u8f96\u533a'), ('530702', u'\u53e4\u57ce\u533a'), ('530721', u'\u7389\u9f99\u7eb3\u897f\u65cf\u81ea\u6cbb\u53bf'), ('530722', u'\u6c38\u80dc\u53bf'), ('530723', u'\u534e\u576a\u53bf'), ('530724', u'\u5b81\u8497\u5f5d\u65cf\u81ea\u6cbb\u53bf'), ('530800', u'\u666e\u6d31\u5e02'), ('530801', u'\u5e02\u8f96\u533a'), ('530802', u'\u601d\u8305\u533a'), ('530821', u'\u5b81\u6d31\u54c8\u5c3c\u65cf\u5f5d\u65cf\u81ea\u6cbb\u53bf'), ('530822', u'\u58a8\u6c5f\u54c8\u5c3c\u65cf\u81ea\u6cbb\u53bf'), ('530823', u'\u666f\u4e1c\u5f5d\u65cf\u81ea\u6cbb\u53bf'), ('530824', u'\u666f\u8c37\u50a3\u65cf\u5f5d\u65cf\u81ea\u6cbb\u53bf'), ('530825', u'\u9547\u6c85\u5f5d\u65cf\u54c8\u5c3c\u65cf\u62c9\u795c\u65cf\u81ea\u6cbb\u53bf'), ('530826', u'\u6c5f\u57ce\u54c8\u5c3c\u65cf\u5f5d\u65cf\u81ea\u6cbb\u53bf'), ('530827', u'\u5b5f\u8fde\u50a3\u65cf\u62c9\u795c\u65cf\u4f64\u65cf\u81ea\u6cbb\u53bf'), ('530828', u'\u6f9c\u6ca7\u62c9\u795c\u65cf\u81ea\u6cbb\u53bf'), ('530829', u'\u897f\u76df\u4f64\u65cf\u81ea\u6cbb\u53bf'), ('530900', u'\u4e34\u6ca7\u5e02'), ('530901', u'\u5e02\u8f96\u533a'), ('530902', u'\u4e34\u7fd4\u533a'), ('530921', u'\u51e4\u5e86\u53bf'), ('530922', u'\u4e91\u53bf'), ('530923', u'\u6c38\u5fb7\u53bf'), ('530924', u'\u9547\u5eb7\u53bf'), ('530925', u'\u53cc\u6c5f\u62c9\u795c\u65cf\u4f64\u65cf\u5e03\u6717\u65cf\u50a3\u65cf\u81ea\u6cbb\u53bf'), ('530926', u'\u803f\u9a6c\u50a3\u65cf\u4f64\u65cf\u81ea\u6cbb\u53bf'), ('530927', u'\u6ca7\u6e90\u4f64\u65cf\u81ea\u6cbb\u53bf'), ('532300', u'\u695a\u96c4\u5f5d\u65cf\u81ea\u6cbb\u5dde'), ('532301', u'\u695a\u96c4\u5e02'), ('532322', u'\u53cc\u67cf\u53bf'), ('532323', u'\u725f\u5b9a\u53bf'), ('532324', u'\u5357\u534e\u53bf'), ('532325', u'\u59da\u5b89\u53bf'), ('532326', u'\u5927\u59da\u53bf'), ('532327', u'\u6c38\u4ec1\u53bf'), ('532328', u'\u5143\u8c0b\u53bf'), ('532329', u'\u6b66\u5b9a\u53bf'), ('532331', u'\u7984\u4e30\u53bf'), ('532500', u'\u7ea2\u6cb3\u54c8\u5c3c\u65cf\u5f5d\u65cf\u81ea\u6cbb\u5dde'), ('532501', u'\u4e2a\u65e7\u5e02'), ('532502', u'\u5f00\u8fdc\u5e02'), ('532503', u'\u8499\u81ea\u5e02'), ('532504', u'\u5f25\u52d2\u5e02'), ('532523', u'\u5c4f\u8fb9\u82d7\u65cf\u81ea\u6cbb\u53bf'), ('532524', u'\u5efa\u6c34\u53bf'), ('532525', u'\u77f3\u5c4f\u53bf'), ('532527', u'\u6cf8\u897f\u53bf'), ('532528', u'\u5143\u9633\u53bf'), ('532529', u'\u7ea2\u6cb3\u53bf'), ('532530', u'\u91d1\u5e73\u82d7\u65cf\u7476\u65cf\u50a3\u65cf\u81ea\u6cbb\u53bf'), ('532531', u'\u7eff\u6625\u53bf'), ('532532', u'\u6cb3\u53e3\u7476\u65cf\u81ea\u6cbb\u53bf'), ('532600', u'\u6587\u5c71\u58ee\u65cf\u82d7\u65cf\u81ea\u6cbb\u5dde'), ('532601', u'\u6587\u5c71\u5e02'), ('532622', u'\u781a\u5c71\u53bf'), ('532623', u'\u897f\u7574\u53bf'), ('532624', u'\u9ebb\u6817\u5761\u53bf'), ('532625', u'\u9a6c\u5173\u53bf'), ('532626', u'\u4e18\u5317\u53bf'), ('532627', u'\u5e7f\u5357\u53bf'), ('532628', u'\u5bcc\u5b81\u53bf'), ('532800', u'\u897f\u53cc\u7248\u7eb3\u50a3\u65cf\u81ea\u6cbb\u5dde'), ('532801', u'\u666f\u6d2a\u5e02'), ('532822', u'\u52d0\u6d77\u53bf'), ('532823', u'\u52d0\u814a\u53bf'), ('532900', u'\u5927\u7406\u767d\u65cf\u81ea\u6cbb\u5dde'), ('532901', u'\u5927\u7406\u5e02'), ('532922', u'\u6f3e\u6fde\u5f5d\u65cf\u81ea\u6cbb\u53bf'), ('532923', u'\u7965\u4e91\u53bf'), ('532924', u'\u5bbe\u5ddd\u53bf'), ('532925', u'\u5f25\u6e21\u53bf'), ('532926', u'\u5357\u6da7\u5f5d\u65cf\u81ea\u6cbb\u53bf'), ('532927', u'\u5dcd\u5c71\u5f5d\u65cf\u56de\u65cf\u81ea\u6cbb\u53bf'), ('532928', u'\u6c38\u5e73\u53bf'), ('532929', u'\u4e91\u9f99\u53bf'), ('532930', u'\u6d31\u6e90\u53bf'), ('532931', u'\u5251\u5ddd\u53bf'), ('532932', u'\u9e64\u5e86\u53bf'), ('533100', u'\u5fb7\u5b8f\u50a3\u65cf\u666f\u9887\u65cf\u81ea\u6cbb\u5dde'), ('533102', u'\u745e\u4e3d\u5e02'), ('533103', u'\u8292\u5e02'), ('533122', u'\u6881\u6cb3\u53bf'), ('533123', u'\u76c8\u6c5f\u53bf'), ('533124', u'\u9647\u5ddd\u53bf'), ('533300', u'\u6012\u6c5f\u5088\u50f3\u65cf\u81ea\u6cbb\u5dde'), ('533321', u'\u6cf8\u6c34\u53bf'), ('533323', u'\u798f\u8d21\u53bf'), ('533324', u'\u8d21\u5c71\u72ec\u9f99\u65cf\u6012\u65cf\u81ea\u6cbb\u53bf'), ('533325', u'\u5170\u576a\u767d\u65cf\u666e\u7c73\u65cf\u81ea\u6cbb\u53bf'), ('533400', u'\u8fea\u5e86\u85cf\u65cf\u81ea\u6cbb\u5dde'), ('533421', u'\u9999\u683c\u91cc\u62c9\u53bf'), ('533422', u'\u5fb7\u94a6\u53bf'), ('533423', u'\u7ef4\u897f\u5088\u50f3\u65cf\u81ea\u6cbb\u53bf'), ('540000', u'\u897f\u85cf\u81ea\u6cbb\u533a'), ('540100', u'\u62c9\u8428\u5e02'), ('540101', u'\u5e02\u8f96\u533a'), ('540102', u'\u57ce\u5173\u533a'), ('540121', u'\u6797\u5468\u53bf'), ('540122', u'\u5f53\u96c4\u53bf'), ('540123', u'\u5c3c\u6728\u53bf'), ('540124', u'\u66f2\u6c34\u53bf'), ('540125', u'\u5806\u9f99\u5fb7\u5e86\u53bf'), ('540126', u'\u8fbe\u5b5c\u53bf'), ('540127', u'\u58a8\u7af9\u5de5\u5361\u53bf'), ('542100', u'\u660c\u90fd\u5730\u533a'), ('542121', u'\u660c\u90fd\u53bf'), ('542122', u'\u6c5f\u8fbe\u53bf'), ('542123', u'\u8d21\u89c9\u53bf'), ('542124', u'\u7c7b\u4e4c\u9f50\u53bf'), ('542125', u'\u4e01\u9752\u53bf'), ('542126', u'\u5bdf\u96c5\u53bf'), ('542127', u'\u516b\u5bbf\u53bf'), ('542128', u'\u5de6\u8d21\u53bf'), ('542129', u'\u8292\u5eb7\u53bf'), ('542132', u'\u6d1b\u9686\u53bf'), ('542133', u'\u8fb9\u575d\u53bf'), ('542200', u'\u5c71\u5357\u5730\u533a'), ('542221', u'\u4e43\u4e1c\u53bf'), ('542222', u'\u624e\u56ca\u53bf'), ('542223', u'\u8d21\u560e\u53bf'), ('542224', u'\u6851\u65e5\u53bf'), ('542225', u'\u743c\u7ed3\u53bf'), ('542226', u'\u66f2\u677e\u53bf'), ('542227', u'\u63aa\u7f8e\u53bf'), ('542228', u'\u6d1b\u624e\u53bf'), ('542229', u'\u52a0\u67e5\u53bf'), ('542231', u'\u9686\u5b50\u53bf'), ('542232', u'\u9519\u90a3\u53bf'), ('542233', u'\u6d6a\u5361\u5b50\u53bf'), ('542300', u'\u65e5\u5580\u5219\u5730\u533a'), ('542301', u'\u65e5\u5580\u5219\u5e02'), ('542322', u'\u5357\u6728\u6797\u53bf'), ('542323', u'\u6c5f\u5b5c\u53bf'), ('542324', u'\u5b9a\u65e5\u53bf'), ('542325', u'\u8428\u8fe6\u53bf'), ('542326', u'\u62c9\u5b5c\u53bf'), ('542327', u'\u6602\u4ec1\u53bf'), ('542328', u'\u8c22\u901a\u95e8\u53bf'), ('542329', u'\u767d\u6717\u53bf'), ('542330', u'\u4ec1\u5e03\u53bf'), ('542331', u'\u5eb7\u9a6c\u53bf'), ('542332', u'\u5b9a\u7ed3\u53bf'), ('542333', u'\u4ef2\u5df4\u53bf'), ('542334', u'\u4e9a\u4e1c\u53bf'), ('542335', u'\u5409\u9686\u53bf'), ('542336', u'\u8042\u62c9\u6728\u53bf'), ('542337', u'\u8428\u560e\u53bf'), ('542338', u'\u5c97\u5df4\u53bf'), ('542400', u'\u90a3\u66f2\u5730\u533a'), ('542421', u'\u90a3\u66f2\u53bf'), ('542422', u'\u5609\u9ece\u53bf'), ('542423', u'\u6bd4\u5982\u53bf'), ('542424', u'\u8042\u8363\u53bf'), ('542425', u'\u5b89\u591a\u53bf'), ('542426', u'\u7533\u624e\u53bf'), ('542427', u'\u7d22\u53bf'), ('542428', u'\u73ed\u6208\u53bf'), ('542429', u'\u5df4\u9752\u53bf'), ('542430', u'\u5c3c\u739b\u53bf'), ('542431', u'\u53cc\u6e56\u53bf'), ('542500', u'\u963f\u91cc\u5730\u533a'), ('542521', u'\u666e\u5170\u53bf'), ('542522', u'\u672d\u8fbe\u53bf'), ('542523', u'\u5676\u5c14\u53bf'), ('542524', u'\u65e5\u571f\u53bf'), ('542525', u'\u9769\u5409\u53bf'), ('542526', u'\u6539\u5219\u53bf'), ('542527', u'\u63aa\u52e4\u53bf'), ('542600', u'\u6797\u829d\u5730\u533a'), ('542621', u'\u6797\u829d\u53bf'), ('542622', u'\u5de5\u5e03\u6c5f\u8fbe\u53bf'), ('542623', u'\u7c73\u6797\u53bf'), ('542624', u'\u58a8\u8131\u53bf'), ('542625', u'\u6ce2\u5bc6\u53bf'), ('542626', u'\u5bdf\u9685\u53bf'), ('542627', u'\u6717\u53bf'), ('610000', u'\u9655\u897f\u7701'), ('610100', u'\u897f\u5b89\u5e02'), ('610101', u'\u5e02\u8f96\u533a'), ('610102', u'\u65b0\u57ce\u533a'), ('610103', u'\u7891\u6797\u533a'), ('610104', u'\u83b2\u6e56\u533a'), ('610111', u'\u705e\u6865\u533a'), ('610112', u'\u672a\u592e\u533a'), ('610113', u'\u96c1\u5854\u533a'), ('610114', u'\u960e\u826f\u533a'), ('610115', u'\u4e34\u6f7c\u533a'), ('610116', u'\u957f\u5b89\u533a'), ('610122', u'\u84dd\u7530\u53bf'), ('610124', u'\u5468\u81f3\u53bf'), ('610125', u'\u6237\u53bf'), ('610126', u'\u9ad8\u9675\u53bf'), ('610200', u'\u94dc\u5ddd\u5e02'), ('610201', u'\u5e02\u8f96\u533a'), ('610202', u'\u738b\u76ca\u533a'), ('610203', u'\u5370\u53f0\u533a'), ('610204', u'\u8000\u5dde\u533a'), ('610222', u'\u5b9c\u541b\u53bf'), ('610300', u'\u5b9d\u9e21\u5e02'), ('610301', u'\u5e02\u8f96\u533a'), ('610302', u'\u6e2d\u6ee8\u533a'), ('610303', u'\u91d1\u53f0\u533a'), ('610304', u'\u9648\u4ed3\u533a'), ('610322', u'\u51e4\u7fd4\u53bf'), ('610323', u'\u5c90\u5c71\u53bf'), ('610324', u'\u6276\u98ce\u53bf'), ('610326', u'\u7709\u53bf'), ('610327', u'\u9647\u53bf'), ('610328', u'\u5343\u9633\u53bf'), ('610329', u'\u9e9f\u6e38\u53bf'), ('610330', u'\u51e4\u53bf'), ('610331', u'\u592a\u767d\u53bf'), ('610400', u'\u54b8\u9633\u5e02'), ('610401', u'\u5e02\u8f96\u533a'), ('610402', u'\u79e6\u90fd\u533a'), ('610403', u'\u6768\u9675\u533a'), ('610404', u'\u6e2d\u57ce\u533a'), ('610422', u'\u4e09\u539f\u53bf'), ('610423', u'\u6cfe\u9633\u53bf'), ('610424', u'\u4e7e\u53bf'), ('610425', u'\u793c\u6cc9\u53bf'), ('610426', u'\u6c38\u5bff\u53bf'), ('610427', u'\u5f6c\u53bf'), ('610428', u'\u957f\u6b66\u53bf'), ('610429', u'\u65ec\u9091\u53bf'), ('610430', u'\u6df3\u5316\u53bf'), ('610431', u'\u6b66\u529f\u53bf'), ('610481', u'\u5174\u5e73\u5e02'), ('610500', u'\u6e2d\u5357\u5e02'), ('610501', u'\u5e02\u8f96\u533a'), ('610502', u'\u4e34\u6e2d\u533a'), ('610521', u'\u534e\u53bf'), ('610522', u'\u6f7c\u5173\u53bf'), ('610523', u'\u5927\u8354\u53bf'), ('610524', u'\u5408\u9633\u53bf'), ('610525', u'\u6f84\u57ce\u53bf'), ('610526', u'\u84b2\u57ce\u53bf'), ('610527', u'\u767d\u6c34\u53bf'), ('610528', u'\u5bcc\u5e73\u53bf'), ('610581', u'\u97e9\u57ce\u5e02'), ('610582', u'\u534e\u9634\u5e02'), ('610600', u'\u5ef6\u5b89\u5e02'), ('610601', u'\u5e02\u8f96\u533a'), ('610602', u'\u5b9d\u5854\u533a'), ('610621', u'\u5ef6\u957f\u53bf'), ('610622', u'\u5ef6\u5ddd\u53bf'), ('610623', u'\u5b50\u957f\u53bf'), ('610624', u'\u5b89\u585e\u53bf'), ('610625', u'\u5fd7\u4e39\u53bf'), ('610626', u'\u5434\u8d77\u53bf'), ('610627', u'\u7518\u6cc9\u53bf'), ('610628', u'\u5bcc\u53bf'), ('610629', u'\u6d1b\u5ddd\u53bf'), ('610630', u'\u5b9c\u5ddd\u53bf'), ('610631', u'\u9ec4\u9f99\u53bf'), ('610632', u'\u9ec4\u9675\u53bf'), ('610700', u'\u6c49\u4e2d\u5e02'), ('610701', u'\u5e02\u8f96\u533a'), ('610702', u'\u6c49\u53f0\u533a'), ('610721', u'\u5357\u90d1\u53bf'), ('610722', u'\u57ce\u56fa\u53bf'), ('610723', u'\u6d0b\u53bf'), ('610724', u'\u897f\u4e61\u53bf'), ('610725', u'\u52c9\u53bf'), ('610726', u'\u5b81\u5f3a\u53bf'), ('610727', u'\u7565\u9633\u53bf'), ('610728', u'\u9547\u5df4\u53bf'), ('610729', u'\u7559\u575d\u53bf'), ('610730', u'\u4f5b\u576a\u53bf'), ('610800', u'\u6986\u6797\u5e02'), ('610801', u'\u5e02\u8f96\u533a'), ('610802', u'\u6986\u9633\u533a'), ('610821', u'\u795e\u6728\u53bf'), ('610822', u'\u5e9c\u8c37\u53bf'), ('610823', u'\u6a2a\u5c71\u53bf'), ('610824', u'\u9756\u8fb9\u53bf'), ('610825', u'\u5b9a\u8fb9\u53bf'), ('610826', u'\u7ee5\u5fb7\u53bf'), ('610827', u'\u7c73\u8102\u53bf'), ('610828', u'\u4f73\u53bf'), ('610829', u'\u5434\u5821\u53bf'), ('610830', u'\u6e05\u6da7\u53bf'), ('610831', u'\u5b50\u6d32\u53bf'), ('610900', u'\u5b89\u5eb7\u5e02'), ('610901', u'\u5e02\u8f96\u533a'), ('610902', u'\u6c49\u6ee8\u533a'), ('610921', u'\u6c49\u9634\u53bf'), ('610922', u'\u77f3\u6cc9\u53bf'), ('610923', u'\u5b81\u9655\u53bf'), ('610924', u'\u7d2b\u9633\u53bf'), ('610925', u'\u5c9a\u768b\u53bf'), ('610926', u'\u5e73\u5229\u53bf'), ('610927', u'\u9547\u576a\u53bf'), ('610928', u'\u65ec\u9633\u53bf'), ('610929', u'\u767d\u6cb3\u53bf'), ('611000', u'\u5546\u6d1b\u5e02'), ('611001', u'\u5e02\u8f96\u533a'), ('611002', u'\u5546\u5dde\u533a'), ('611021', u'\u6d1b\u5357\u53bf'), ('611022', u'\u4e39\u51e4\u53bf'), ('611023', u'\u5546\u5357\u53bf'), ('611024', u'\u5c71\u9633\u53bf'), ('611025', u'\u9547\u5b89\u53bf'), ('611026', u'\u67de\u6c34\u53bf'), ('620000', u'\u7518\u8083\u7701'), ('620100', u'\u5170\u5dde\u5e02'), ('620101', u'\u5e02\u8f96\u533a'), ('620102', u'\u57ce\u5173\u533a'), ('620103', u'\u4e03\u91cc\u6cb3\u533a'), ('620104', u'\u897f\u56fa\u533a'), ('620105', u'\u5b89\u5b81\u533a'), ('620111', u'\u7ea2\u53e4\u533a'), ('620121', u'\u6c38\u767b\u53bf'), ('620122', u'\u768b\u5170\u53bf'), ('620123', u'\u6986\u4e2d\u53bf'), ('620200', u'\u5609\u5cea\u5173\u5e02'), ('620201', u'\u5e02\u8f96\u533a'), ('620300', u'\u91d1\u660c\u5e02'), ('620301', u'\u5e02\u8f96\u533a'), ('620302', u'\u91d1\u5ddd\u533a'), ('620321', u'\u6c38\u660c\u53bf'), ('620400', u'\u767d\u94f6\u5e02'), ('620401', u'\u5e02\u8f96\u533a'), ('620402', u'\u767d\u94f6\u533a'), ('620403', u'\u5e73\u5ddd\u533a'), ('620421', u'\u9756\u8fdc\u53bf'), ('620422', u'\u4f1a\u5b81\u53bf'), ('620423', u'\u666f\u6cf0\u53bf'), ('620500', u'\u5929\u6c34\u5e02'), ('620501', u'\u5e02\u8f96\u533a'), ('620502', u'\u79e6\u5dde\u533a'), ('620503', u'\u9ea6\u79ef\u533a'), ('620521', u'\u6e05\u6c34\u53bf'), ('620522', u'\u79e6\u5b89\u53bf'), ('620523', u'\u7518\u8c37\u53bf'), ('620524', u'\u6b66\u5c71\u53bf'), ('620525', u'\u5f20\u5bb6\u5ddd\u56de\u65cf\u81ea\u6cbb\u53bf'), ('620600', u'\u6b66\u5a01\u5e02'), ('620601', u'\u5e02\u8f96\u533a'), ('620602', u'\u51c9\u5dde\u533a'), ('620621', u'\u6c11\u52e4\u53bf'), ('620622', u'\u53e4\u6d6a\u53bf'), ('620623', u'\u5929\u795d\u85cf\u65cf\u81ea\u6cbb\u53bf'), ('620700', u'\u5f20\u6396\u5e02'), ('620701', u'\u5e02\u8f96\u533a'), ('620702', u'\u7518\u5dde\u533a'), ('620721', u'\u8083\u5357\u88d5\u56fa\u65cf\u81ea\u6cbb\u53bf'), ('620722', u'\u6c11\u4e50\u53bf'), ('620723', u'\u4e34\u6cfd\u53bf'), ('620724', u'\u9ad8\u53f0\u53bf'), ('620725', u'\u5c71\u4e39\u53bf'), ('620800', u'\u5e73\u51c9\u5e02'), ('620801', u'\u5e02\u8f96\u533a'), ('620802', u'\u5d06\u5cd2\u533a'), ('620821', u'\u6cfe\u5ddd\u53bf'), ('620822', u'\u7075\u53f0\u53bf'), ('620823', u'\u5d07\u4fe1\u53bf'), ('620824', u'\u534e\u4ead\u53bf'), ('620825', u'\u5e84\u6d6a\u53bf'), ('620826', u'\u9759\u5b81\u53bf'), ('620900', u'\u9152\u6cc9\u5e02'), ('620901', u'\u5e02\u8f96\u533a'), ('620902', u'\u8083\u5dde\u533a'), ('620921', u'\u91d1\u5854\u53bf'), ('620922', u'\u74dc\u5dde\u53bf'), ('620923', u'\u8083\u5317\u8499\u53e4\u65cf\u81ea\u6cbb\u53bf'), ('620924', u'\u963f\u514b\u585e\u54c8\u8428\u514b\u65cf\u81ea\u6cbb\u53bf'), ('620981', u'\u7389\u95e8\u5e02'), ('620982', u'\u6566\u714c\u5e02'), ('621000', u'\u5e86\u9633\u5e02'), ('621001', u'\u5e02\u8f96\u533a'), ('621002', u'\u897f\u5cf0\u533a'), ('621021', u'\u5e86\u57ce\u53bf'), ('621022', u'\u73af\u53bf'), ('621023', u'\u534e\u6c60\u53bf'), ('621024', u'\u5408\u6c34\u53bf'), ('621025', u'\u6b63\u5b81\u53bf'), ('621026', u'\u5b81\u53bf'), ('621027', u'\u9547\u539f\u53bf'), ('621100', u'\u5b9a\u897f\u5e02'), ('621101', u'\u5e02\u8f96\u533a'), ('621102', u'\u5b89\u5b9a\u533a'), ('621121', u'\u901a\u6e2d\u53bf'), ('621122', u'\u9647\u897f\u53bf'), ('621123', u'\u6e2d\u6e90\u53bf'), ('621124', u'\u4e34\u6d2e\u53bf'), ('621125', u'\u6f33\u53bf'), ('621126', u'\u5cb7\u53bf'), ('621200', u'\u9647\u5357\u5e02'), ('621201', u'\u5e02\u8f96\u533a'), ('621202', u'\u6b66\u90fd\u533a'), ('621221', u'\u6210\u53bf'), ('621222', u'\u6587\u53bf'), ('621223', u'\u5b95\u660c\u53bf'), ('621224', u'\u5eb7\u53bf'), ('621225', u'\u897f\u548c\u53bf'), ('621226', u'\u793c\u53bf'), ('621227', u'\u5fbd\u53bf'), ('621228', u'\u4e24\u5f53\u53bf'), ('622900', u'\u4e34\u590f\u56de\u65cf\u81ea\u6cbb\u5dde'), ('622901', u'\u4e34\u590f\u5e02'), ('622921', u'\u4e34\u590f\u53bf'), ('622922', u'\u5eb7\u4e50\u53bf'), ('622923', u'\u6c38\u9756\u53bf'), ('622924', u'\u5e7f\u6cb3\u53bf'), ('622925', u'\u548c\u653f\u53bf'), ('622926', u'\u4e1c\u4e61\u65cf\u81ea\u6cbb\u53bf'), ('622927', u'\u79ef\u77f3\u5c71\u4fdd\u5b89\u65cf\u4e1c\u4e61\u65cf\u6492\u62c9\u65cf\u81ea\u6cbb\u53bf'), ('623000', u'\u7518\u5357\u85cf\u65cf\u81ea\u6cbb\u5dde'), ('623001', u'\u5408\u4f5c\u5e02'), ('623021', u'\u4e34\u6f6d\u53bf'), ('623022', u'\u5353\u5c3c\u53bf'), ('623023', u'\u821f\u66f2\u53bf'), ('623024', u'\u8fed\u90e8\u53bf'), ('623025', u'\u739b\u66f2\u53bf'), ('623026', u'\u788c\u66f2\u53bf'), ('623027', u'\u590f\u6cb3\u53bf'), ('630000', u'\u9752\u6d77\u7701'), ('630100', u'\u897f\u5b81\u5e02'), ('630101', u'\u5e02\u8f96\u533a'), ('630102', u'\u57ce\u4e1c\u533a'), ('630103', u'\u57ce\u4e2d\u533a'), ('630104', u'\u57ce\u897f\u533a'), ('630105', u'\u57ce\u5317\u533a'), ('630121', u'\u5927\u901a\u56de\u65cf\u571f\u65cf\u81ea\u6cbb\u53bf'), ('630122', u'\u6e5f\u4e2d\u53bf'), ('630123', u'\u6e5f\u6e90\u53bf'), ('630200', u'\u6d77\u4e1c\u5e02'), ('630202', u'\u4e50\u90fd\u533a'), ('630221', u'\u5e73\u5b89\u53bf'), ('630222', u'\u6c11\u548c\u56de\u65cf\u571f\u65cf\u81ea\u6cbb\u53bf'), ('630223', u'\u4e92\u52a9\u571f\u65cf\u81ea\u6cbb\u53bf'), ('630224', u'\u5316\u9686\u56de\u65cf\u81ea\u6cbb\u53bf'), ('630225', u'\u5faa\u5316\u6492\u62c9\u65cf\u81ea\u6cbb\u53bf'), ('632200', u'\u6d77\u5317\u85cf\u65cf\u81ea\u6cbb\u5dde'), ('632221', u'\u95e8\u6e90\u56de\u65cf\u81ea\u6cbb\u53bf'), ('632222', u'\u7941\u8fde\u53bf'), ('632223', u'\u6d77\u664f\u53bf'), ('632224', u'\u521a\u5bdf\u53bf'), ('632300', u'\u9ec4\u5357\u85cf\u65cf\u81ea\u6cbb\u5dde'), ('632321', u'\u540c\u4ec1\u53bf'), ('632322', u'\u5c16\u624e\u53bf'), ('632323', u'\u6cfd\u5e93\u53bf'), ('632324', u'\u6cb3\u5357\u8499\u53e4\u65cf\u81ea\u6cbb\u53bf'), ('632500', u'\u6d77\u5357\u85cf\u65cf\u81ea\u6cbb\u5dde'), ('632521', u'\u5171\u548c\u53bf'), ('632522', u'\u540c\u5fb7\u53bf'), ('632523', u'\u8d35\u5fb7\u53bf'), ('632524', u'\u5174\u6d77\u53bf'), ('632525', u'\u8d35\u5357\u53bf'), ('632600', u'\u679c\u6d1b\u85cf\u65cf\u81ea\u6cbb\u5dde'), ('632621', u'\u739b\u6c81\u53bf'), ('632622', u'\u73ed\u739b\u53bf'), ('632623', u'\u7518\u5fb7\u53bf'), ('632624', u'\u8fbe\u65e5\u53bf'), ('632625', u'\u4e45\u6cbb\u53bf'), ('632626', u'\u739b\u591a\u53bf'), ('632700', u'\u7389\u6811\u85cf\u65cf\u81ea\u6cbb\u5dde'), ('632701', u'\u7389\u6811\u5e02'), ('632722', u'\u6742\u591a\u53bf'), ('632723', u'\u79f0\u591a\u53bf'), ('632724', u'\u6cbb\u591a\u53bf'), ('632725', u'\u56ca\u8c26\u53bf'), ('632726', u'\u66f2\u9ebb\u83b1\u53bf'), ('632800', u'\u6d77\u897f\u8499\u53e4\u65cf\u85cf\u65cf\u81ea\u6cbb\u5dde'), ('632801', u'\u683c\u5c14\u6728\u5e02'), ('632802', u'\u5fb7\u4ee4\u54c8\u5e02'), ('632821', u'\u4e4c\u5170\u53bf'), ('632822', u'\u90fd\u5170\u53bf'), ('632823', u'\u5929\u5cfb\u53bf'), ('640000', u'\u5b81\u590f\u56de\u65cf\u81ea\u6cbb\u533a'), ('640100', u'\u94f6\u5ddd\u5e02'), ('640101', u'\u5e02\u8f96\u533a'), ('640104', u'\u5174\u5e86\u533a'), ('640105', u'\u897f\u590f\u533a'), ('640106', u'\u91d1\u51e4\u533a'), ('640121', u'\u6c38\u5b81\u53bf'), ('640122', u'\u8d3a\u5170\u53bf'), ('640181', u'\u7075\u6b66\u5e02'), ('640200', u'\u77f3\u5634\u5c71\u5e02'), ('640201', u'\u5e02\u8f96\u533a'), ('640202', u'\u5927\u6b66\u53e3\u533a'), ('640205', u'\u60e0\u519c\u533a'), ('640221', u'\u5e73\u7f57\u53bf'), ('640300', u'\u5434\u5fe0\u5e02'), ('640301', u'\u5e02\u8f96\u533a'), ('640302', u'\u5229\u901a\u533a'), ('640303', u'\u7ea2\u5bfa\u5821\u533a'), ('640323', u'\u76d0\u6c60\u53bf'), ('640324', u'\u540c\u5fc3\u53bf'), ('640381', u'\u9752\u94dc\u5ce1\u5e02'), ('640400', u'\u56fa\u539f\u5e02'), ('640401', u'\u5e02\u8f96\u533a'), ('640402', u'\u539f\u5dde\u533a'), ('640422', u'\u897f\u5409\u53bf'), ('640423', u'\u9686\u5fb7\u53bf'), ('640424', u'\u6cfe\u6e90\u53bf'), ('640425', u'\u5f6d\u9633\u53bf'), ('640500', u'\u4e2d\u536b\u5e02'), ('640501', u'\u5e02\u8f96\u533a'), ('640502', u'\u6c99\u5761\u5934\u533a'), ('640521', u'\u4e2d\u5b81\u53bf'), ('640522', u'\u6d77\u539f\u53bf'), ('650000', u'\u65b0\u7586\u7ef4\u543e\u5c14\u81ea\u6cbb\u533a'), ('650100', u'\u4e4c\u9c81\u6728\u9f50\u5e02'), ('650101', u'\u5e02\u8f96\u533a'), ('650102', u'\u5929\u5c71\u533a'), ('650103', u'\u6c99\u4f9d\u5df4\u514b\u533a'), ('650104', u'\u65b0\u5e02\u533a'), ('650105', u'\u6c34\u78e8\u6c9f\u533a'), ('650106', u'\u5934\u5c6f\u6cb3\u533a'), ('650107', u'\u8fbe\u5742\u57ce\u533a'), ('650109', u'\u7c73\u4e1c\u533a'), ('650121', u'\u4e4c\u9c81\u6728\u9f50\u53bf'), ('650200', u'\u514b\u62c9\u739b\u4f9d\u5e02'), ('650201', u'\u5e02\u8f96\u533a'), ('650202', u'\u72ec\u5c71\u5b50\u533a'), ('650203', u'\u514b\u62c9\u739b\u4f9d\u533a'), ('650204', u'\u767d\u78b1\u6ee9\u533a'), ('650205', u'\u4e4c\u5c14\u79be\u533a'), ('652100', u'\u5410\u9c81\u756a\u5730\u533a'), ('652101', u'\u5410\u9c81\u756a\u5e02'), ('652122', u'\u912f\u5584\u53bf'), ('652123', u'\u6258\u514b\u900a\u53bf'), ('652200', u'\u54c8\u5bc6\u5730\u533a'), ('652201', u'\u54c8\u5bc6\u5e02'), ('652222', u'\u5df4\u91cc\u5764\u54c8\u8428\u514b\u81ea\u6cbb\u53bf'), ('652223', u'\u4f0a\u543e\u53bf'), ('652300', u'\u660c\u5409\u56de\u65cf\u81ea\u6cbb\u5dde'), ('652301', u'\u660c\u5409\u5e02'), ('652302', u'\u961c\u5eb7\u5e02'), ('652323', u'\u547c\u56fe\u58c1\u53bf'), ('652324', u'\u739b\u7eb3\u65af\u53bf'), ('652325', u'\u5947\u53f0\u53bf'), ('652327', u'\u5409\u6728\u8428\u5c14\u53bf'), ('652328', u'\u6728\u5792\u54c8\u8428\u514b\u81ea\u6cbb\u53bf'), ('652700', u'\u535a\u5c14\u5854\u62c9\u8499\u53e4\u81ea\u6cbb\u5dde'), ('652701', u'\u535a\u4e50\u5e02'), ('652702', u'\u963f\u62c9\u5c71\u53e3\u5e02'), ('652722', u'\u7cbe\u6cb3\u53bf'), ('652723', u'\u6e29\u6cc9\u53bf'), ('652800', u'\u5df4\u97f3\u90ed\u695e\u8499\u53e4\u81ea\u6cbb\u5dde'), ('652801', u'\u5e93\u5c14\u52d2\u5e02'), ('652822', u'\u8f6e\u53f0\u53bf'), ('652823', u'\u5c09\u7281\u53bf'), ('652824', u'\u82e5\u7f8c\u53bf'), ('652825', u'\u4e14\u672b\u53bf'), ('652826', u'\u7109\u8006\u56de\u65cf\u81ea\u6cbb\u53bf'), ('652827', u'\u548c\u9759\u53bf'), ('652828', u'\u548c\u7855\u53bf'), ('652829', u'\u535a\u6e56\u53bf'), ('652900', u'\u963f\u514b\u82cf\u5730\u533a'), ('652901', u'\u963f\u514b\u82cf\u5e02'), ('652922', u'\u6e29\u5bbf\u53bf'), ('652923', u'\u5e93\u8f66\u53bf'), ('652924', u'\u6c99\u96c5\u53bf'), ('652925', u'\u65b0\u548c\u53bf'), ('652926', u'\u62dc\u57ce\u53bf'), ('652927', u'\u4e4c\u4ec0\u53bf'), ('652928', u'\u963f\u74e6\u63d0\u53bf'), ('652929', u'\u67ef\u576a\u53bf'), ('653000', u'\u514b\u5b5c\u52d2\u82cf\u67ef\u5c14\u514b\u5b5c\u81ea\u6cbb\u5dde'), ('653001', u'\u963f\u56fe\u4ec0\u5e02'), ('653022', u'\u963f\u514b\u9676\u53bf'), ('653023', u'\u963f\u5408\u5947\u53bf'), ('653024', u'\u4e4c\u6070\u53bf'), ('653100', u'\u5580\u4ec0\u5730\u533a'), ('653101', u'\u5580\u4ec0\u5e02'), ('653121', u'\u758f\u9644\u53bf'), ('653122', u'\u758f\u52d2\u53bf'), ('653123', u'\u82f1\u5409\u6c99\u53bf'), ('653124', u'\u6cfd\u666e\u53bf'), ('653125', u'\u838e\u8f66\u53bf'), ('653126', u'\u53f6\u57ce\u53bf'), ('653127', u'\u9ea6\u76d6\u63d0\u53bf'), ('653128', u'\u5cb3\u666e\u6e56\u53bf'), ('653129', u'\u4f3d\u5e08\u53bf'), ('653130', u'\u5df4\u695a\u53bf'), ('653131', u'\u5854\u4ec0\u5e93\u5c14\u5e72\u5854\u5409\u514b\u81ea\u6cbb\u53bf'), ('653200', u'\u548c\u7530\u5730\u533a'), ('653201', u'\u548c\u7530\u5e02'), ('653221', u'\u548c\u7530\u53bf'), ('653222', u'\u58a8\u7389\u53bf'), ('653223', u'\u76ae\u5c71\u53bf'), ('653224', u'\u6d1b\u6d66\u53bf'), ('653225', u'\u7b56\u52d2\u53bf'), ('653226', u'\u4e8e\u7530\u53bf'), ('653227', u'\u6c11\u4e30\u53bf'), ('654000', u'\u4f0a\u7281\u54c8\u8428\u514b\u81ea\u6cbb\u5dde'), ('654002', u'\u4f0a\u5b81\u5e02'), ('654003', u'\u594e\u5c6f\u5e02'), ('654021', u'\u4f0a\u5b81\u53bf'), ('654022', u'\u5bdf\u5e03\u67e5\u5c14\u9521\u4f2f\u81ea\u6cbb\u53bf'), ('654023', u'\u970d\u57ce\u53bf'), ('654024', u'\u5de9\u7559\u53bf'), ('654025', u'\u65b0\u6e90\u53bf'), ('654026', u'\u662d\u82cf\u53bf'), ('654027', u'\u7279\u514b\u65af\u53bf'), ('654028', u'\u5c3c\u52d2\u514b\u53bf'), ('654200', u'\u5854\u57ce\u5730\u533a'), ('654201', u'\u5854\u57ce\u5e02'), ('654202', u'\u4e4c\u82cf\u5e02'), ('654221', u'\u989d\u654f\u53bf'), ('654223', u'\u6c99\u6e7e\u53bf'), ('654224', u'\u6258\u91cc\u53bf'), ('654225', u'\u88d5\u6c11\u53bf'), ('654226', u'\u548c\u5e03\u514b\u8d5b\u5c14\u8499\u53e4\u81ea\u6cbb\u53bf'), ('654300', u'\u963f\u52d2\u6cf0\u5730\u533a'), ('654301', u'\u963f\u52d2\u6cf0\u5e02'), ('654321', u'\u5e03\u5c14\u6d25\u53bf'), ('654322', u'\u5bcc\u8574\u53bf'), ('654323', u'\u798f\u6d77\u53bf'), ('654324', u'\u54c8\u5df4\u6cb3\u53bf'), ('654325', u'\u9752\u6cb3\u53bf'), ('654326', u'\u5409\u6728\u4e43\u53bf'), ('659000', u'\u81ea\u6cbb\u533a\u76f4\u8f96\u53bf\u7ea7\u884c\u653f\u533a\u5212'), ('659001', u'\u77f3\u6cb3\u5b50\u5e02'), ('659002', u'\u963f\u62c9\u5c14\u5e02'), ('659003', u'\u56fe\u6728\u8212\u514b\u5e02'), ('659004', u'\u4e94\u5bb6\u6e20\u5e02'), ('710000', u'\u53f0\u6e7e\u7701'), ('810000', u'\u9999\u6e2f\u7279\u522b\u884c\u653f\u533a'), ('820000', u'\u6fb3\u95e8\u7279\u522b\u884c\u653f\u533a')]
        province_id = None
        province_name = None
        city_id = None
        city_name = None
        for item in cn:
            # global province_id, province_name, city_id
            if item[0].endswith('0000'):
                province = Province(cn_id=item[0], province=item[1])
                db.session.add(province)
                db.session.commit()
                province_id = province.id
                province_name = item[1]
            elif item[0].endswith('00'):
                if item[1] == u'市辖区':
                    if province_name in directly_city:
                        name = province_name
                    else:
                        continue
                elif item[1] == u'县':
                    continue
                else:
                    name = item[1]
                city = City(cn_id=item[0], city=name, province_id=province_id)
                db.session.add(city)
                db.session.commit()
                city_id = city.id
                city_name = item[1]
            else:
                district = District(cn_id=item[0], district=item[1], city_id=city_id)
                db.session.add(district)
                db.session.commit()


class Address(Property):
    id = db.Column(db.Integer, primary_key=True)
    cn_id = db.Column(db.Integer, nullable=False)
    address = db.Column(db.Unicode(30), nullable=False)
    created = db.Column(db.Integer, default=time.time, nullable=False)

    _flush = {
        'area': lambda x: District.query.filter_by(cn_id=x.cn_id).limit(1).first() or \
        City.query.filter_by(cn_id=x.cn_id).limit(1).first() or \
        Province.filter_by(cn_id=x.cn_id).limit(1).first()
    }
    _area = None

    @property
    def area(self):
        return self.get_or_flush('area')

    def vague_address(self):
        return self.area.area_address() if self.area else ''

    def precise_address(self):
        return '%s%s' % (self.vague_address(), self.address)


class UserAddress(Address, db.Model):
    __tablename__ = 'user_addresses'
    user_id = db.Column(db.Integer, nullable=False)
    mobile = db.Column(db.CHAR(11), unique=True, nullable=False)


class VendorAddress(Address, db.Model):
    __tablename__ = 'vendor_addresses'
    vendor_id = db.Column(db.Integer, nullable=False)

    def __init__(self, vendor_id, cn_id, address):
        self.vendor_id = vendor_id
        self.cn_id = cn_id
        self.address = address


class DistributorAddress(Address, db.Model):
    __tablename__ = 'distributor_addresses'
    distributor_id = db.Column(db.Integer, nullable=False)

    def __init__(self, distributor_id, cn_id, address):
        self.distributor_id = distributor_id
        self.cn_id = cn_id
        self.address = address


class Stove(db.Model):
    __tablename__ = 'stoves'
    id = db.Column(db.Integer, primary_key=True)
    stove = db.Column(db.Unicode(10), nullable=False)

    @staticmethod
    def generate_fake():
        for stove in (u'水煮', u'蒸汽', u'煮蜡'):
            db.session.add(Stove(stove=stove))
        db.session.commit()


class Carve(db.Model):
    __tablename__ = 'carves'
    id = db.Column(db.Integer, primary_key=True)
    carve = db.Column(db.Unicode(10), nullable=False)

    @staticmethod
    def generate_fake():
        for carve in (u"透雕", u"浮雕", u"浅浮雕", u"镂空雕", u"圆雕(立体雕)", u"微雕", u"阴阳额雕", u"阴雕", u"通雕"):
            db.session.add(Carve(carve=carve))
        db.session.commit()


class Sand(db.Model):
    __tablename__ = 'sands'
    id = db.Column(db.Integer, primary_key=True)
    sand = db.Column(db.Integer, nullable=False)

    @staticmethod
    def generate_fake():
        for sand in (180, 280, 320, 400, 600, 800, 1000, 1200, 1500, 2000, 2500, 3000, 4000, 5000):
            db.session.add(Sand(sand=sand))
        db.session.commit()


class Paint(db.Model):
    __tablename__ = 'paints'
    id = db.Column(db.Integer, primary_key=True)
    paint = db.Column(db.Unicode(10), nullable=False)

    @staticmethod
    def generate_fake():
        for paint in (u"生漆", u"烫蜡"):
            db.session.add(Paint(paint=paint))
        db.session.commit()


class Decoration(db.Model):
    __tablename__ = 'decorations'
    id = db.Column(db.Integer, primary_key=True)
    decoration = db.Column(db.Unicode(10), nullable=False)

    @staticmethod
    def generate_fake():
        for decoration in (u"白铜镶嵌", u"黄铜镶嵌", u"石料镶嵌"):
            db.session.add(Decoration(decoration=decoration))
        db.session.commit()


class Tenon(db.Model):
    __tablename__ = 'tenons'
    id = db.Column(db.Integer, primary_key=True)
    tenon = db.Column(db.Unicode(10), nullable=False)

    @staticmethod
    def generate_fake():
        for tenon in (u'燕尾榫', u'明榫', u'暗榫', u'楔钉榫', u'套榫', u'抱肩榫', u'勾挂榫', u'夹头榫', u'插肩榫', u'走马销', u'平榫'):
            db.session.add(Tenon(tenon=tenon))
        db.session.commit()


class ItemTenon(db.Model):
    __tablename__ = 'item_tenons'
    id = db.Column(db.Integer, primary_key=True)
    item_id = db.Column(db.Integer, nullable=False)
    tenon_id = db.Column(db.Integer, nullable=False)


@login_manager.user_loader
def load_user(user_id):
    id_ = int(user_id[1:])
    if user_id.startswith(privilege_id_prefix):
        return Privilege.query.get(id_)
    elif user_id.startswith(vendor_id_prefix):
        return Vendor.query.get(id_)
    elif user_id.startswith(distributor_id_prefix):
        return Distributor.query.get(id_)
    return User.query.get(id_)


def generate_fake_data():
    FirstCategory.generate_fake()
    SecondCategory.generate_fake()
    Material.generate_fake()
    District.generate_fake()
    Stove.generate_fake()
    Carve.generate_fake()
    Sand.generate_fake()
    Paint.generate_fake()
    Decoration.generate_fake()
    Tenon.generate_fake()
    FirstScene.generate_fake()
    SecondScene.generate_fake()
    Vendor.generate_fake()
    Privilege.generate_fake()
