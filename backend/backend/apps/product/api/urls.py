from django.urls import URLPattern, path, include, re_path
from rest_framework.routers import DefaultRouter
from product.api.views import AllProductListView, AllSearchView, BrandWithProductsView, CatSubcatListView, DuplicateProductListView, GetCitiesView, GetStatesView, ProductListInCategory, ProductListInSubCategory, ProductNameListView, ProductView, ProductListView,ProductBrandView, ProductCategoryView, ProductFeedbackView\
    , ProductImagesView, ProductPriceView, ProductRatingView, ProductSubCategoryView, ProductReviewView, HeaderScrollableView\
        , ProductImageView, ShowRoomeView, SubCategoryProductListView, TagView, ProductSearchView, BrandSearchView, CategorySearchView\
             , TagSearchView, PriceRangeView, CartRegistView, CategoryPaginationView, PincodeValidation, AddressView\
            , ProductSubCategoryTypeView, AdminBrandView, AdminProductView, AdminSubCatView, AdminSubcatTypeView, WishlistProductView, confirm_payment, get_product_colour, product_inserter,\
            user_address, category_insert, subcategory_insert, brand_insert,TagsListWithProductsView,\
            CategoriesWithProductsView, TotalProductsView, TotalBrandsView,orders_statistics,initiate_payment, product_updater, UserOrderSummaryView

app_name = "product"

router = DefaultRouter()
router.register('productregist', ProductView)
# router.register('getproductregist', GetProductView)
router.register('productlistregist', ProductListView)
router.register('brandregist', ProductBrandView)
router.register('cartregist', CartRegistView)
router.register('categoryregist', ProductCategoryView)
router.register('feedbackregist', ProductFeedbackView)
router.register('productimagesregist', ProductImagesView)
router.register('priceregist', ProductPriceView)
router.register('ratingregist', ProductRatingView)
router.register('subcategoryregist', ProductSubCategoryView)
router.register('reviewregist', ProductReviewView)
router.register('headregist', HeaderScrollableView)
# router.register('ordersregist', UserOrdersView)
router.register('imagesregist', ProductImageView)
router.register('showroomregist', ShowRoomeView)
router.register('tagregist', TagView)
router.register('address', AddressView)
router.register('subcategorytyperegist', ProductSubCategoryTypeView)
router.register('adminbrandregist', AdminBrandView)
router.register('admincategoryregist', AdminProductView)
router.register('adminsubcategoryregist', AdminSubCatView)
router.register('adminsubcategorytyperegist', AdminSubcatTypeView)
router.register('categories-products-list', CategoriesWithProductsView , basename='category')
router.register('brand-products-list/(?P<brand_id>\d+)', BrandWithProductsView , basename='brand')
router.register('tags-products-list', TagsListWithProductsView , basename='tags')
router.register('orders', UserOrderSummaryView)
router.register('cat-product-list', ProductListInCategory, basename='products')
router.register('subcat-product-list', ProductListInSubCategory, basename='products')

urlpatterns = [
    path('', include(router.urls)),
    re_path('^prodsearch/(?P<Productsearch>.+)/$', ProductSearchView.as_view()),
    re_path('^brandsearch/(?P<brandsearch>.+)/$', BrandSearchView.as_view()),
    re_path('^catsearch/(?P<categorysearch>.+)/$', CategorySearchView.as_view()),
    re_path('^tagsearch/(?P<Tagsearch>.+)/$', TagSearchView.as_view()),
    re_path('^pricerange/(?P<price>.+)/$', PriceRangeView.as_view()),
    #re_path('^cartlist', ProductCartView.as_view()),
    re_path('^catpage/(?P<categorysearch>.+)/$', CategoryPaginationView.as_view()),
    re_path('^pincode', PincodeValidation),
    # path('search', SearchView.as_view(), name='product-search'),
    path('total-products', TotalProductsView.as_view(), name='total-products'),
    path('total-brands', TotalBrandsView.as_view(), name='total-brands'),
    path('productinsert', product_inserter),
    path('productupdate', product_updater),
    path('useraddress', user_address),
    path('categoryinsert', category_insert),
    path('subcategoryinsert', subcategory_insert),
    path('brandinsert', brand_insert),
    path('order-stats', orders_statistics),
    path('payu_payment_initiate', initiate_payment, name='payu_payment_initiate'),
    path('payment-conf', confirm_payment, name='confirm_payment'),
    path('cat-subcat-list', CatSubcatListView.as_view(), name='product-category-list'),
    path('search', AllSearchView.as_view(), name='search-all'),
    path('product-name', ProductNameListView.as_view(), name='product-names'),
    path('subcat-products-list', SubCategoryProductListView.as_view(), name='subcategory-products'),
    path('subcat-products-list/<int:id>', SubCategoryProductListView.as_view(), name='subcategory-products'),
    path('get-states', GetStatesView.as_view(), name='get-states-from-erp'),
    path('get-cities', GetCitiesView.as_view(), name='get-cities-from-erp'),
    path('wishlistitems', WishlistProductView.as_view(), name='wishlist-items'),
    path('duplicateproducts', DuplicateProductListView.as_view(), name='duplicate-products'),
    path('allproductlistview', AllProductListView.as_view(), name='all-products'),
    path('product-color', get_product_colour, name='get-product-colour'),
]
