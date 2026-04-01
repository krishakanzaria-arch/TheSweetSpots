from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import datetime, timedelta

UserAuth = get_user_model()


# -----------------------------
# Location & company structure
# -----------------------------
class State(models.Model):
    state_name = models.CharField(max_length=50, unique=True)

    def __str__(self):
        return self.state_name


class City(models.Model):
    state = models.ForeignKey(State, on_delete=models.PROTECT, related_name='cities')
    city_name = models.CharField(max_length=50)

    class Meta:
        unique_together = ('state', 'city_name')

    def __str__(self):
        return f'{self.city_name}, {self.state.state_name}'


class Company(models.Model):
    company_name = models.CharField(max_length=100, unique=True)
    address = models.CharField(max_length=255, blank=True)
    city = models.ForeignKey(City, on_delete=models.PROTECT, related_name='companies')
    pincode = models.CharField(max_length=10, blank=True)
    mobile_no = models.CharField(max_length=15, blank=True)
    phone_no = models.CharField(max_length=15, blank=True)
    invoice_ser = models.CharField(max_length=20, blank=True)

    def __str__(self):
        return self.company_name


class Role(models.Model):
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='roles')
    role_name = models.CharField(max_length=50)

    class Meta:
        unique_together = ('company', 'role_name')

    def __str__(self):
        return f'{self.role_name} @ {self.company.company_name}'


# -----------------------------
# Users & delivery personnel
# -----------------------------
class UserProfile(models.Model):
    """
    Maps ERD 'User' to a profile linked to Django auth user.
    """
    user = models.OneToOneField(UserAuth, on_delete=models.CASCADE, related_name='profile')
    first_name = models.CharField(max_length=30)
    last_name = models.CharField(max_length=30, blank=True)
    mobile_no = models.CharField(max_length=15, blank=True)
    email = models.EmailField(max_length=254)
    address = models.CharField(max_length=255, blank=True)
    city = models.ForeignKey(City, on_delete=models.PROTECT, related_name='user_profiles')
    role = models.ForeignKey(Role, on_delete=models.PROTECT, related_name='user_profiles', null=True)

    def __str__(self):
        return f'{self.first_name} {self.last_name}'.strip()

class PasswordResetOTP(models.Model):
    mobile_no=models.CharField(max_length=15)
    otp=models.CharField(max_length=6)
    created_at=models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.mobile_no

class DeliveryPerson(models.Model):
    first_name = models.CharField(max_length=30)
    last_name = models.CharField(max_length=30, blank=True)
    email = models.EmailField(max_length=254)
    mobile_no = models.CharField(max_length=15)
    address = models.CharField(max_length=255, blank=True)
    city = models.ForeignKey(City, on_delete=models.PROTECT, related_name='delivery_people')

    def __str__(self):
        return f'{self.first_name} {self.last_name}'.strip()


class Area(models.Model):
    """
    ERD shows pincode_id and pincode; we use a standard PK and unique pincode.
    """
    city = models.ForeignKey(City, on_delete=models.PROTECT, related_name='areas')
    pincode = models.CharField(max_length=10, unique=True)
    area_name = models.CharField(max_length=50)

    class Meta:
        unique_together = ('city', 'area_name')

    def __str__(self):
        return f'{self.area_name} ({self.pincode})'


# -----------------------------
# Catalog: categories & products
# -----------------------------
class ProductCategory(models.Model):
    category_name = models.CharField(max_length=50, unique=True)
    description = models.CharField(max_length=255, blank=True)

    def __str__(self):
        return self.category_name


class ProductSubCategory(models.Model):
    product_category = models.ForeignKey(ProductCategory, on_delete=models.CASCADE, related_name='subcategories')
    sub_category_name = models.CharField(max_length=50)

    class Meta:
        unique_together = ('product_category', 'sub_category_name')

    def __str__(self):
        return f'{self.sub_category_name} ({self.product_category.category_name})'


class Product(models.Model):
    product_name = models.CharField(max_length=100)
    product_desc = models.TextField(blank=True)
    product_price = models.DecimalField(max_digits=10, decimal_places=2)
    product_image = models.ImageField(upload_to='products/', blank=True, null=True)
    product_category = models.ForeignKey(ProductCategory, on_delete=models.CASCADE, related_name='products')
    product_sub_category = models.ForeignKey(ProductSubCategory, on_delete=models.CASCADE, related_name='products')
    product_madeof = models.TextField(blank=True)
    stock=models.PositiveIntegerField(default=0)

    class Meta:
        unique_together = ('product_name', 'product_sub_category')

    def __str__(self):
        return self.product_name
    
    @property
    def total_stock(self):
        return sum(batch.quantity for batch in self.batches.all())
    
    @property
    def next_expiry(self):
        batch = self.batches.filter(
        expiry_date__gte=timezone.now().date(),
        quantity__gt=0
    ).order_by('expiry_date').first()

        return batch.expiry_date if batch else None

class Image(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='images')
    image_path = models.CharField(max_length=255, blank=True)  # optional legacy path
    image_name = models.CharField(max_length=125, blank=True)
    file = models.ImageField(upload_to='products/gallery/', blank=True, null=True)

    def __str__(self):
        return self.image_name or f'Image for {self.product_id}'


class Offer(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='offers')
    offer_name = models.CharField(max_length=50)
    start_date = models.DateField()
    end_date = models.DateField()

    class Meta:
        unique_together = ('product', 'offer_name')

    def __str__(self):
        return f'{self.offer_name} on {self.product.product_name}'

class Coupon(models.Model):
    code = models.CharField(max_length=20, unique=True)
    discount_amount = models.PositiveIntegerField()
    is_active = models.BooleanField(default=True)
    expiry_date=models.DateField(null=True,blank=True)

    def is_valid(self):
        return self.is_active and self.expiry_date >= timezone.now().date()

    def __str__(self):
        return self.code

class ProductReview(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='reviews')
    user = models.ForeignKey(UserProfile, on_delete=models.CASCADE)
    rating = models.IntegerField(choices=[
        (1, '1 Star'),
        (2, '2 Stars'),
        (3, '3 Stars'),
        (4, '4 Stars'),
        (5, '5 Stars'),
    ])
    comment = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def _str_(self):
        return f"{self.product.name} - {self.rating}⭐"

class Rating(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='ratings')
    rating_desc = models.CharField(max_length=100)

    def __str__(self):
        return f'Rating for {self.product_id}'


class Feedback(models.Model):
    user = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name='feedbacks')
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='feedbacks')
    feedback_desc = models.CharField(max_length=255)

    class Meta:
        unique_together = ('user', 'product')

    def __str__(self):
        return f'Feedback by {self.user_id} on {self.product_id}'


# -----------------------------
# Cart & orders
# -----------------------------
class Payment(models.Model):
    PAYMENT_TYPE_CHOICES = [
        ('CASH', 'Cash'),
        ('CARD', 'Card'),
        ('UPI', 'UPI'),
        ('WALLET', 'Wallet'),
        ('OTHER', 'Other'),
    ]
    PAYMENT_STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('SUCCESS', 'Success'),
        ('FAILED', 'Failed'),
        ('REFUNDED', 'Refunded'),
    ]

    payment_type = models.CharField(max_length=15, choices=PAYMENT_TYPE_CHOICES)
    payment_status = models.CharField(max_length=10, choices=PAYMENT_STATUS_CHOICES, default='pending')

    def __str__(self):
        return f'{self.payment_type} - {self.payment_status}'


class Order(models.Model):
    PAYMENT_MODE_CHOICES = [
        ('COD', 'Cash on Delivery'),
        ('PREPAID', 'Prepaid'),
    ]
    PAYMENT_STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('PAID', 'Paid'),
        ('FAILED', 'Failed'),
        ('REFUNDED', 'Refunded'),
    ]
    ORDER_STATUS_CHOICES=(
        ('PENDING', 'PENDING'),
        ('CONFIRMED', 'CONFIRMED'),
        ('SHIPPED', 'SHIPPED'),
        ('DELIVERED', 'DELIVERED'),
        ('CANCELLED', 'CANCELLED'),
    )

    user = models.ForeignKey(UserProfile, on_delete=models.PROTECT, related_name='orders')
    order_date = models.DateField(auto_now_add=True)
    delivery_date = models.DateField(blank=True, null=True)
    delivery_charge = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    gst_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2)
    payment_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    payment_status = models.CharField(max_length=10, choices=PAYMENT_STATUS_CHOICES, default='PENDING')
    payment_mode = models.CharField(max_length=20, choices=PAYMENT_MODE_CHOICES, default='COD')
    order_status=models.CharField(max_length=20, choices=ORDER_STATUS_CHOICES, default='PENDING')
    coupon=models.ForeignKey(Coupon,on_delete=models.SET_NULL,null=True,blank=True)
    payment = models.OneToOneField(Payment, on_delete=models.CASCADE,null=True, blank=True)

    def can_return(self):
        if self.order_status != 'DELIVERED' or not self.delivery_date:
            return False
        return timezone.now().date() <= self.delivery_date + timedelta(days=1)

    def __str__(self):
        return f'Order #{self.pk} by {self.user_id}'


class OrderDetail(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='details')
    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name='order_details')
    qty = models.PositiveIntegerField()
    price = models.DecimalField(max_digits=10, decimal_places=2)  # unit price at time of order

    class Meta:
        unique_together = ('order', 'product')

    def __str__(self):
        return f'{self.qty} x {self.product.product_name} (Order {self.order_id})'


class CartItem(models.Model):
    """
    ERD 'Cart' is a junction of user and product with qty/price.
    """
    user = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name='cart_items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='cart_items')
    qty = models.PositiveIntegerField(default=1)
    price = models.DecimalField(max_digits=10, decimal_places=2)  # current price snapshot

    class Meta:
        unique_together = ('user', 'product')

    def __str__(self):
        return f'{self.qty} x {self.product.product_name} in {self.user_id} cart'


class CustomerOrder(models.Model):
    """
    Separate custom order entity with special instructions.
    """
    user = models.ForeignKey(UserProfile, on_delete=models.PROTECT, related_name='customer_orders')
    price = models.DecimalField(max_digits=12, decimal_places=2)
    special_instructions = models.CharField(max_length=255, blank=True)

    def __str__(self):
        return f'CustomerOrder #{self.pk} by {self.user_id}'


class OrderReturn(models.Model):
    STATUS_CHOICES=(
        ('REQUESTED','Requested'),
        ('APPROVED','approved'),
        ('REJECTED','rejected'),
    )
    order = models.ForeignKey(Order, on_delete=models.PROTECT, related_name='returns')
    return_date = models.DateField(auto_now_add=True)
    status=models.CharField(max_length=20,choices=STATUS_CHOICES,default='REQUESTED')

    def __str__(self):
        return f'Return #{self.pk}-{self.status}'


class OrderReturnDetail(models.Model):
    order_return = models.ForeignKey(OrderReturn, on_delete=models.CASCADE, related_name='details')
    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name='return_details')
    qty = models.PositiveIntegerField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    reason_for_return = models.CharField(max_length=255, blank=True)

    class Meta:
        unique_together = ('order_return', 'product')

    def __str__(self):
        return f'Return {self.qty} x {self.product.product_name} (Return {self.order_return_id})'


class Delivery(models.Model):
    delivery_person = models.ForeignKey(DeliveryPerson, on_delete=models.PROTECT, related_name='deliveries')
    order = models.ForeignKey(Order, on_delete=models.PROTECT, related_name='deliveries')
    delivery_date = models.DateField(blank=True, null=True)

    class Meta:
        unique_together = ('delivery_person', 'order')

    def __str__(self):
        return f'Delivery of Order {self.order_id} by {self.delivery_person_id}'


# -----------------------------
# Support & interactions
# -----------------------------
class Complain(models.Model):
    user = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name='complains')
    complain_name = models.CharField(max_length=125)
    complain_desc = models.CharField(max_length=255, blank=True)
    complain_date = models.DateField(auto_now_add=True)

    def __str__(self):
        return f'{self.complain_name} ({self.user_id})'


# -----------------------------
# Inventory & procurement
# -----------------------------
class BatchDetail(models.Model):
    batch_name = models.CharField(max_length=50)
    batch_exp_date = models.DateField(blank=True, null=True)

    def __str__(self):
        return self.batch_name


class RawMaterial(models.Model):
    raw_material_name = models.CharField(max_length=50, unique=True)
    raw_material_type = models.CharField(max_length=20)

    def __str__(self):
        return self.raw_material_name


class Supplier(models.Model):
    first_name = models.CharField(max_length=30)
    last_name = models.CharField(max_length=30, blank=True)
    email = models.EmailField(max_length=254)
    mobile_no = models.CharField(max_length=15)
    supplier_area = models.CharField(max_length=255, blank=True)
    supplier_name = models.CharField(max_length=100)
    invoice_ser = models.CharField(max_length=20, blank=True)
    invoice_ser_id = models.CharField(max_length=20, blank=True)

    def __str__(self):
        return self.supplier_name


class Purchase(models.Model):
    purchase_date = models.DateField(auto_now_add=True)
    supplier = models.ForeignKey(Supplier, on_delete=models.PROTECT, related_name='purchases')
    amount = models.DecimalField(max_digits=12, decimal_places=2)

    def __str__(self):
        return f'Purchase #{self.pk} from {self.supplier_id}'


class PurchaseDetail(models.Model):
    purchase = models.ForeignKey(Purchase, on_delete=models.CASCADE, related_name='details')
    raw_material = models.ForeignKey(RawMaterial, on_delete=models.PROTECT, related_name='purchase_details')
    qty = models.DecimalField(max_digits=10, decimal_places=2)
    price = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        unique_together = ('purchase', 'raw_material')

    def __str__(self):
        return f'{self.qty} {self.raw_material.raw_material_name} (Purchase {self.purchase_id})'


class PurchaseReturn(models.Model):
    purchase = models.ForeignKey(Purchase, on_delete=models.PROTECT, related_name='returns')
    purchase_return_date = models.DateField(auto_now_add=True)

    def __str__(self):
        return f'PurchaseReturn #{self.pk} for Purchase {self.purchase_id}'


class PurchaseReturnDetail(models.Model):
    purchase_return = models.ForeignKey(PurchaseReturn, on_delete=models.CASCADE, related_name='details')
    raw_material = models.ForeignKey(RawMaterial, on_delete=models.PROTECT, related_name='purchase_return_details')
    qty = models.DecimalField(max_digits=10, decimal_places=2)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    reason = models.CharField(max_length=255, blank=True)

    class Meta:
        unique_together = ('purchase_return', 'raw_material')

    def __str__(self):
        return f'Return {self.qty} {self.raw_material.raw_material_name} (PR {self.purchase_return_id})'


class Production(models.Model):
    """
    ERD shows production linked to raw_material; batch optional.
    """
    production_date = models.DateField(auto_now_add=True)
    raw_material = models.ForeignKey(RawMaterial, on_delete=models.PROTECT, related_name='productions')
    batch = models.ForeignKey(BatchDetail, on_delete=models.SET_NULL, related_name='productions', null=True, blank=True)

    def __str__(self):
        return f'Production #{self.pk} on {self.production_date}'

class CustomCakeOrder(models.Model):

    SHAPE_CHOICES = [
        ('round', 'Round'),
        ('square', 'Square'),
        ('heart', 'Heart'),
    ]

    PAYMENT_CHOICES = [
        ('cod', 'Cash on Delivery'),
        ('razorpay', 'Razorpay'),
    ]
    order=models.ForeignKey(Order,on_delete=models.CASCADE,related_name='custom_cakes',null=True,blank=True)
    shape = models.CharField(max_length=20, choices=SHAPE_CHOICES)
    layers = models.IntegerField()
    cream = models.CharField(max_length=50)
    filling_color = models.CharField(max_length=50, blank=True, null=True)
    topping = models.CharField(max_length=50)
    cake_name = models.CharField(max_length=200)
    price = models.IntegerField()

    cake_image = models.TextField()  # base64 image

    payment_method = models.CharField(max_length=20, choices=PAYMENT_CHOICES)
    is_confirmed = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Custom Order #{self.id} - {self.shape}"

class ProductBatch(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="batches")
    batch_number = models.CharField(max_length=50)
    quantity = models.PositiveIntegerField()
    expiry_date = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.product.product_name} - {self.batch_number}"

# Create your models here.
