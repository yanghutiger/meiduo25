

def get_breadcrumb(category):
    breadcrumb = {"cat1": category.parent.parent,
                  "cat2": category.parent,
                  "cat3": category
                  }
    return breadcrumb