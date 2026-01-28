from django.urls import path

from apps.ai.views import StallMarkView, StallMarkBazaarChoiceView, StallMarkModerateView, \
    StallMarkModerateBazaarChoiceView, StallAiTest, StallAiTestBazaar, StallMarkUpdateView, \
    StallMarkUpdateBazaarChoiceView

app_name = 'ai'
urlpatterns = [
    path("stall-mark/", StallMarkBazaarChoiceView.as_view(), name="stall-mark-bazaar"),
    path("stall-mark/<int:pk>/", StallMarkView.as_view(), name="stall-mark"),
    path("stall-mark-moderate/", StallMarkModerateBazaarChoiceView.as_view(), name="stall-mark-moderate-bazaar"),
    path("stall-mark-moderate/<int:pk>/", StallMarkModerateView.as_view(), name="stall-mark-moderate"),
    path("stall-mark-update/", StallMarkUpdateBazaarChoiceView.as_view(), name="stall-mark-update-bazaar"),
    path("stall-mark-update/<int:pk>/", StallMarkUpdateView.as_view(), name="stall-mark-update"),
    path("stall-test/", StallAiTestBazaar.as_view(), name="stall-test-bazaar"),
    path("stall-test/<int:pk>/", StallAiTest.as_view(), name="stall-test"),
]
