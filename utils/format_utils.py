
def camel(snake):
    return ''.join(map(str.title, snake.split('_')))