from django.urls import path

from subscription import views

urlpatterns = [
    path("subscription-cart/add-to-cart/", views.cart_add_to_cart, name="subscription-cart-add"),
    path("subscription-cart/items/", views.cart_items, name="subscription-cart-items"),
    path("subscription-cart/increment/", views.cart_increment, name="subscription-cart-increment"),
    path("subscription-cart/decrement/", views.cart_decrement, name="subscription-cart-decrement"),
    path("subscription-cart/<int:pk>/remove/", views.cart_remove, name="subscription-cart-remove"),
    path("subscription-cart/checkout/", views.cart_checkout, name="subscription-cart-checkout"),
]

